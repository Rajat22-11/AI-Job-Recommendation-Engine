import logging
from datetime import date

import pandas as pd

from job_aggregator.domain.models import SourceStatus
from job_aggregator.fetching.job_boards.jobspy_board_fetcher import JobSpyBoardFetcher, build_searches
from job_aggregator.registry.source_entry import SourceEntry

SOURCE = SourceEntry(id="naukri", name="Naukri", fetch_method="jobspy_board", enabled=True,
                     settings={"site": "naukri", "max_searches": 2})


def _frame(rows):
    return pd.DataFrame(rows)


ROW = {
    "id": "nk-1", "site": "naukri", "job_url": "https://www.naukri.com/job-1", "job_url_direct": float("nan"),
    "title": "Java Developer", "company": "Acme", "location": "Pune, Maharashtra", "date_posted": date(2026, 11, 7),
    "job_type": "fulltime", "interval": "yearly", "min_amount": 600000.0, "max_amount": 900000.0, "currency": "INR",
    "is_remote": False, "description": "Spring Boot", "skills": "Java, Spring Boot", "experience_range": "1-3 Yrs",
}


def test_results_mapped_to_common_shape(app_settings, search_config):
    calls = []

    def scrape(**kwargs):
        calls.append(kwargs)
        return _frame([ROW])

    result = JobSpyBoardFetcher(app_settings.jobspy, scrape).fetch(SOURCE, search_config)
    assert result.status is SourceStatus.SUCCEEDED
    listing = result.listings[0]  # same job from two searches is kept once
    assert len(result.listings) == 1
    assert listing.apply_url == "https://www.naukri.com/job-1" and listing.apply_url_kind == "board"
    assert listing.salary_text == "INR 600,000 - 900,000 per year"
    assert listing.skills == ["Java", "Spring Boot"] and listing.experience_text == "1-3 Yrs"
    assert listing.posted_at == date(2026, 11, 7)
    assert len(calls) == 2 and calls[0]["site_name"] == ["naukri"] and calls[0]["country_indeed"] == "india"
    assert calls[0]["search_term"] == "java"


def test_exception_with_429_marks_blocked_and_stops(app_settings, search_config):
    calls = []

    def scrape(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("Response 429 Too Many Requests")

    result = JobSpyBoardFetcher(app_settings.jobspy, scrape).fetch(SOURCE, search_config)
    assert result.status is SourceStatus.BLOCKED and "429" in result.message
    assert len(calls) == 1


def test_logged_403_marks_blocked(app_settings, search_config):
    def scrape(**kwargs):
        site_logger = logging.getLogger("JobSpy:Naukri")
        site_logger.propagate = False  # as JobSpy configures it
        site_logger.error("Naukri API request failed: 403 Client Error: Forbidden")
        return _frame([])

    result = JobSpyBoardFetcher(app_settings.jobspy, scrape).fetch(SOURCE, search_config)
    assert result.status is SourceStatus.BLOCKED


def test_empty_result_is_success_with_zero(app_settings, search_config):
    result = JobSpyBoardFetcher(app_settings.jobspy, lambda **kw: _frame([])).fetch(SOURCE, search_config)
    assert result.status is SourceStatus.SUCCEEDED and result.listings == []


def test_unrelated_error_on_every_search_is_failed(app_settings, search_config):
    def scrape(**kwargs):
        raise ValueError("unexpected page layout")

    result = JobSpyBoardFetcher(app_settings.jobspy, scrape).fetch(SOURCE, search_config)
    assert result.status is SourceStatus.FAILED


def test_remote_location_becomes_remote_search_in_india(search_config):
    searches = build_searches(search_config, 100)
    assert ("java", "India", True) in searches
    assert ("java", "Pune", False) in searches


def test_cap_is_spread_across_keywords_and_locations_with_live_config():
    from job_aggregator.domain.models import SearchConfig
    live = SearchConfig(
        keywords=["java spring boot developer", "java backend engineer", "software engineer java",
                  "machine learning engineer", "AI engineer", "data scientist", "data engineer",
                  "full stack java react"],
        locations=["Pune", "Mumbai", "Ahmedabad", "Gandhinagar GIFT City", "Surat", "Vadodara", "Remote India",
                   "Remote International"],
        min_salary_lpa=8.2, max_required_yoe=2, max_job_age_days=30)
    searches = build_searches(live, 12)
    assert len(searches) == 12 and len(set(searches)) == 12
    assert len({term for term, _, _ in searches}) == 8  # every keyword is used
    assert {loc for _, loc, _ in searches} >= {"India", "Pune", "Mumbai"}  # remote India and cities
    assert not any("international" in loc.lower() for _, loc, _ in searches)
    assert any(remote for _, _, remote in searches)
