"""Contract tests for We Work Remotely, Working Nomads and Arc, using saved real payloads."""

import json
from datetime import date

import httpx
import pytest

from job_aggregator.domain.models import SearchConfig, SourceStatus
from job_aggregator.fetching.feeds.weworkremotely_feed_fetcher import WeWorkRemotelyFeedFetcher
from job_aggregator.fetching.keyword_matching import KeywordMatcher
from job_aggregator.fetching.open_api.workingnomads_fetcher import WorkingNomadsFetcher
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.fetching.web_pages.arc_fetcher import ArcFetcher, page_job_lists
from job_aggregator.registry.load_source_registry import load_not_fetched, validate_not_fetched
from job_aggregator.registry.source_entry import SourceEntry
from tests.conftest import FIXTURES, REPO_ROOT

EVERYTHING = SearchConfig(keywords=[], locations=[], min_salary_lpa=0, max_required_yoe=10, max_job_age_days=30)
JAVA = SearchConfig(keywords=["java spring boot developer", "java backend engineer"], locations=["Pune"],
                    min_salary_lpa=8.2, max_required_yoe=2, max_job_age_days=30)


def _http(app_settings, handler):
    return PoliteHttpClient(app_settings.fetching, transport=httpx.MockTransport(handler), sleep=lambda s: None)


def _entry(source_id, method, **settings):
    return SourceEntry(id=source_id, name=source_id, fetch_method=method, enabled=True, settings=settings)


# ---------------- We Work Remotely ----------------

def test_weworkremotely_feed_contract(app_settings):
    rss = (FIXTURES / "weworkremotely.rss").read_text(encoding="utf-8")
    fetcher = WeWorkRemotelyFeedFetcher(_http(app_settings, lambda r: httpx.Response(200, text=rss)))
    result = fetcher.fetch(_entry("weworkremotely", "rss_feed", provider="weworkremotely", feeds=["https://x/f.rss"],
                                  region_words=["anywhere", "worldwide"]), EVERYTHING)
    assert result.status is SourceStatus.SUCCEEDED and result.listings
    first = result.listings[0]
    assert first.company == "Squarespace" and first.title == "Staff Software Engineer, Revenue Systems"
    assert first.location == "Remote (Anywhere in the World)" and first.is_remote
    assert first.source_url.startswith("https://weworkremotely.com/remote-jobs/")  # original link kept
    assert first.posted_at == date(2026, 10, 18)


def test_weworkremotely_drops_regions_closed_to_india(app_settings):
    rss = (FIXTURES / "weworkremotely.rss").read_text(encoding="utf-8")
    fetcher = WeWorkRemotelyFeedFetcher(_http(app_settings, lambda r: httpx.Response(200, text=rss)))
    nowhere = fetcher.fetch(_entry("weworkremotely", "rss_feed", provider="weworkremotely", feeds=["https://x/f.rss"],
                                   region_words=["antarctica"]), EVERYTHING)
    assert nowhere.listings == []


def test_weworkremotely_rejects_malicious_xml(app_settings):
    from defusedxml import DefusedXmlException

    bomb = ('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]>'
            "<rss><channel>&b;</channel></rss>")
    fetcher = WeWorkRemotelyFeedFetcher(_http(app_settings, lambda r: httpx.Response(200, text=bomb)))
    with pytest.raises(DefusedXmlException):
        fetcher.fetch(_entry("weworkremotely", "rss_feed", provider="weworkremotely", feeds=["https://x/f.rss"]),
                      EVERYTHING)


# ---------------- Working Nomads ----------------

def test_workingnomads_contract(app_settings):
    payload = json.loads((FIXTURES / "workingnomads_search.json").read_text(encoding="utf-8"))
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    fetcher = WorkingNomadsFetcher(_http(app_settings, handler))
    source = _entry("workingnomads", "open_api", provider="workingnomads", location_words=["germany", "usa"])
    result = fetcher.fetch(source, JAVA)
    assert len(requests) == 2 and requests[0].url.params["q"] == "java spring boot developer"
    first = result.listings[0]
    assert first.title == "Java developer" and first.company == "Blackbird Collective"
    assert first.apply_url.startswith("https://jobs.smartrecruiters.com/")          # employer's own link
    assert first.source_url == "https://www.workingnomads.com/jobs/java-developer-blackbird-collective-1935727"
    assert first.apply_url_kind == "employer" and first.skills[:2] == ["java", "aws"]
    assert len({listing.source_url for listing in result.listings}) == len(result.listings)  # de-duplicated


def test_workingnomads_keeps_only_locations_open_to_india(app_settings):
    payload = json.loads((FIXTURES / "workingnomads_search.json").read_text(encoding="utf-8"))
    fetcher = WorkingNomadsFetcher(_http(app_settings, lambda r: httpx.Response(200, json=payload)))
    result = fetcher.fetch(_entry("workingnomads", "open_api", provider="workingnomads",
                                  location_words=["anywhere", "india"]), EVERYTHING)
    assert result.listings == []  # the fixture's jobs are restricted to Germany and the USA


# ---------------- Arc ----------------

def test_arc_page_job_lists_read_embedded_data():
    html = (FIXTURES / "arc_remote_jobs.html").read_text(encoding="utf-8")
    arc_jobs, external_jobs = page_job_lists(html)
    assert len(arc_jobs) == 2 and len(external_jobs) == 4
    assert page_job_lists("<html>no data</html>") == ([], [])


def test_arc_contract_keeps_jobs_open_to_india_only(app_settings):
    html = (FIXTURES / "arc_remote_jobs.html").read_text(encoding="utf-8")
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(200, text=html)

    fetcher = ArcFetcher(_http(app_settings, handler), KeywordMatcher.from_settings(app_settings.matching))
    result = fetcher.fetch(_entry("arc", "web_page", provider="arc", skill_pages=["java"]), JAVA)
    assert requested == ["https://arc.dev/remote-jobs/java"]
    by_title = {listing.title: listing for listing in result.listings}
    assert "Senior Java Engineer - Core/Infra - Elasticsearch" not in by_title  # Poland only
    worldwide = by_title["Senior Java Developer - Fulltime - Worldwide"]
    assert worldwide.apply_url.startswith("https://arc.dev/remote-jobs/details/senior-java-developer-fulltime-")
    assert worldwide.employment_type == "contract" and worldwide.location == "Remote (Worldwide)"
    assert all(listing.source_url.startswith("https://arc.dev/remote-jobs/") for listing in result.listings)


def test_arc_external_job_open_to_india_is_kept_with_board_link(app_settings):
    html = (FIXTURES / "arc_remote_jobs.html").read_text(encoding="utf-8")
    everything = EVERYTHING
    fetcher = ArcFetcher(_http(app_settings, lambda r: httpx.Response(200, text=html)))
    result = fetcher.fetch(_entry("arc", "web_page", provider="arc", skill_pages=["java"]), everything)
    jitterbit = next(job for job in result.listings if job.company == "Jitterbit")
    assert jitterbit.apply_url.startswith("https://arc.dev/remote-jobs/j/jitterbit-senior-software-engineer")
    assert jitterbit.apply_url_kind == "board"


# ---------------- not_fetched section ----------------

def test_real_registry_has_reasons_for_every_other_enabled_source():
    reasons = load_not_fetched(REPO_ROOT / "config" / "sources.yaml")
    assert {"wellfound", "foundit", "jobspresso", "hiringcafe", "upwork"} <= set(reasons)
    assert all(len(reason) > 10 for reason in reasons.values())


def test_not_fetched_rejects_source_listed_twice_or_without_reason():
    from job_aggregator.domain.errors import InvalidRegistryError

    with pytest.raises(InvalidRegistryError, match="both"):
        validate_not_fetched({"sources": [{"id": "arc"}], "not_fetched": {"arc": "x"}})
    with pytest.raises(InvalidRegistryError, match="reason"):
        validate_not_fetched({"sources": [], "not_fetched": {"arc": ""}})
