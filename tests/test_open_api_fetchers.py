import json
from datetime import UTC, date, datetime

import httpx

from job_aggregator.domain.models import SourceRunRecord, SourceStatus
from job_aggregator.fetching.open_api.himalayas_fetcher import HimalayasFetcher
from job_aggregator.fetching.open_api.jobcode_fetcher import JobcodeFetcher
from job_aggregator.fetching.open_api.remoteok_fetcher import RemoteOkFetcher
from job_aggregator.fetching.open_api.remotive_fetcher import RemotiveFetcher
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.persistence.run_repository import RunRepository
from job_aggregator.registry.source_entry import SourceEntry
from tests.conftest import FIXTURES
from tests.fakes import FakeDatabaseClient

NOW = datetime(2026, 11, 8, 15, 0, tzinfo=UTC)


def _fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _http(app_settings, payload, seen_requests=None):
    def handler(request):
        if seen_requests is not None:
            seen_requests.append(request)
        return httpx.Response(200, json=payload)

    return PoliteHttpClient(app_settings.fetching, transport=httpx.MockTransport(handler), sleep=lambda s: None)


def _entry(source_id, provider, **settings):
    return SourceEntry(id=source_id, name=source_id, fetch_method="open_api", enabled=True,
                       settings={"provider": provider, **settings})


def test_jobcode_contract(app_settings, search_config):
    requests = []
    fetcher = JobcodeFetcher(_http(app_settings, _fixture("jobcode_posts.json"), requests),
                             last_success_lookup=lambda source_id: datetime(2026, 11, 5, tzinfo=UTC), now=lambda: NOW)
    source = _entry("jobcode", "jobcode", category_ids=[48, 138], excluded_category_ids=[52], max_pages=1)
    result = fetcher.fetch(source, search_config)
    oracle = next(listing for listing in result.listings if listing.company == "Oracle")
    assert oracle.title == "Support Engineer 1"
    assert oracle.apply_url == "https://careers.oracle.com/en/sites/jobsearch/job/349168"
    assert oracle.location == "Bengaluru, Karnataka, India"
    assert oracle.experience_text == "0 to 2+ Years"
    assert oracle.source_url.startswith("https://jobcode.in/")
    assert oracle.posted_at == date(2026, 11, 8)
    assert "SQL" in oracle.skills
    assert len(result.listings) == 3
    assert requests[0].url.params["after"] == "2026-11-04T00:00:00"  # last success minus one day
    assert requests[0].url.params["categories_exclude"] == "52"


def test_jobcode_lookback_floor_when_never_succeeded(app_settings, search_config):
    requests = []
    fetcher = JobcodeFetcher(_http(app_settings, [], requests), lambda s: None, now=lambda: NOW)
    fetcher.fetch(_entry("jobcode", "jobcode", lookback_days=30), search_config)
    assert requests[0].url.params["after"] == "2026-10-09T15:00:00"


def test_himalayas_contract(app_settings, search_config):
    fetcher = HimalayasFetcher(_http(app_settings, _fixture("himalayas_search.json")))
    result = fetcher.fetch(_entry("himalayas", "himalayas", max_pages=1, max_keywords=1), search_config)
    first = result.listings[0]
    assert first.title == "Java Lead" and first.company == "Cloud Counselage Pvt Ltd"
    assert first.location == "Remote (India)" and first.is_remote
    assert first.source_url.startswith("https://himalayas.app/")  # original link kept for attribution
    assert first.posted_at is not None
    assert len(result.listings) == 3


def test_remotive_contract_and_daily_cap_across_runs(app_settings, search_config):
    db = FakeDatabaseClient()
    runs = RunRepository(db)
    requests = []
    fetcher = RemotiveFetcher(_http(app_settings, _fixture("remotive_jobs.json"), requests),
                              calls_made_today=lambda source_id: runs.count_source_calls_today(source_id, NOW))
    source = _entry("remotive", "remotive", max_calls_per_day=2)
    statuses = []
    for run in range(3):
        result = fetcher.fetch(source, search_config)
        statuses.append(result.status)
        runs.record_source_run(f"r{run}", SourceRunRecord(source_id="remotive", status=result.status,
                                                          started_at=NOW, message=result.message))
    assert statuses == [SourceStatus.SUCCEEDED, SourceStatus.SUCCEEDED, SourceStatus.SKIPPED]
    assert len(requests) == 2


def test_remotive_listing_shape(app_settings):
    from job_aggregator.domain.models import SearchConfig

    everything = SearchConfig(keywords=[], locations=[], min_salary_lpa=0, max_required_yoe=10, max_job_age_days=30)
    fetcher = RemotiveFetcher(_http(app_settings, _fixture("remotive_jobs.json")), calls_made_today=lambda s: 0)
    result = fetcher.fetch(_entry("remotive", "remotive"), everything)
    first = result.listings[0]
    assert first.source_url.startswith("https://remotive.com/") and first.is_remote
    assert first.location.startswith("Remote (")
    assert "24 hours" in result.message


def test_remoteok_skips_legal_notice_and_keeps_url(app_settings):
    from job_aggregator.domain.models import SearchConfig

    everything = SearchConfig(keywords=[], locations=[], min_salary_lpa=0, max_required_yoe=10, max_job_age_days=30)
    payload = _fixture("remoteok_api.json")
    result = RemoteOkFetcher(_http(app_settings, payload)).fetch(_entry("remoteok", "remoteok"), everything)
    assert len(result.listings) == len(payload) - 1
    first = result.listings[0]
    assert first.title == "Feltsense AI Engineer" and first.company == "Silver.dev"
    assert first.source_url.lower().startswith("https://remoteok.com/remote-jobs/")
    assert first.salary_text == "$60,000 - $110,000 per year"
    assert "Remote OK" in result.message
