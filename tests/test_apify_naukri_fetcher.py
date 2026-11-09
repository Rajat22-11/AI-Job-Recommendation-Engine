"""Naukri through Apify: mapping of a saved real actor output, search parameters, rotation and failure."""

import json

import pytest

from job_aggregator.credentials.credential_pool import CredentialPool
from job_aggregator.domain.models import SearchConfig, SourceStatus
from job_aggregator.fetching.job_boards.apify_naukri_fetcher import ApifyNaukriFetcher, naukri_item_to_listing
from job_aggregator.registry.source_entry import SourceEntry
from tests.conftest import FIXTURES

ITEMS = json.loads((FIXTURES / "apify_naukri_items.json").read_text(encoding="utf-8"))
CONFIG = SearchConfig(keywords=["java developer", "data engineer"], locations=["Pune", "Remote India"],
                      min_salary_lpa=8.2, max_required_yoe=2, max_job_age_days=30)


def _source(**settings):
    return SourceEntry(id="naukri", name="Naukri", fetch_method="apify_job_board", enabled=True,
                       settings={"provider": "naukri", **settings})


def test_actor_item_maps_to_listing():
    listing = naukri_item_to_listing(ITEMS[0], "naukri")
    assert listing.title == "Software Engineer" and listing.company == "Bajaj Finance"
    assert listing.apply_url.startswith("https://www.naukri.com/job-listing") and listing.apply_url_kind == "board"
    assert listing.location == "Pune" and listing.experience_text == "1-4 Yrs"
    assert listing.posted_at.isoformat() == "2026-11-05"
    assert "Java Development" in listing.skills
    assert naukri_item_to_listing({"title": "x"}, "naukri") is None  # no company or link


def test_sends_small_capped_searches_with_experience_and_freshness():
    calls = []

    def runner(token, actor_id, run_input):
        calls.append((token, actor_id, run_input))
        return ITEMS

    result = ApifyNaukriFetcher(CredentialPool("apify", ["t1"]), runner).fetch(
        _source(max_searches=2, max_jobs_per_search=7, freshness_days=2), CONFIG)
    assert len(calls) == 2 and result.status is SourceStatus.SUCCEEDED
    token, actor_id, run_input = calls[0]
    assert actor_id == "srd836/naukri-jobs-scraper" and run_input["maxJobs"] == 7
    assert run_input["freshness"] == 2 and run_input["experience"] == 2
    assert len(result.listings) == len({item["jobUrl"] for item in ITEMS})  # same jobs from two searches: de-duplicated


def test_rotates_to_next_token_on_quota_error():
    used = []

    def runner(token, actor_id, run_input):
        used.append(token)
        if token == "t1":
            raise RuntimeError("Monthly usage hard limit exceeded")
        return ITEMS

    result = ApifyNaukriFetcher(CredentialPool("apify", ["t1", "t2"]), runner).fetch(_source(max_searches=1), CONFIG)
    assert used == ["t1", "t2"] and result.status is SourceStatus.SUCCEEDED


def test_all_tokens_exhausted_fails_with_a_clear_message():
    def runner(token, actor_id, run_input):
        raise RuntimeError("Monthly usage hard limit exceeded")

    result = ApifyNaukriFetcher(CredentialPool("apify", ["t1"]), runner).fetch(_source(max_searches=3), CONFIG)
    assert result.status is SourceStatus.FAILED and "out of quota" in result.message


def test_one_failing_search_keeps_the_others_as_partial():
    state = {"n": 0}

    def runner(token, actor_id, run_input):
        state["n"] += 1
        if state["n"] == 1:
            raise ValueError("actor crashed")
        return ITEMS

    result = ApifyNaukriFetcher(CredentialPool("apify", ["t1"]), runner).fetch(_source(max_searches=2), CONFIG)
    assert result.status is SourceStatus.PARTIAL and result.listings


@pytest.mark.parametrize("missing", ["provider"])
def test_registry_requires_provider(missing):
    from job_aggregator.registry.source_entry import FETCH_METHOD_REQUIRED_SETTINGS
    assert missing in FETCH_METHOD_REQUIRED_SETTINGS["apify_job_board"]
