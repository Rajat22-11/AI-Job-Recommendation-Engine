import json

import httpx

from job_aggregator.domain.models import SearchConfig, SourceStatus
from job_aggregator.fetching.ats_boards.ashby_board_fetcher import AshbyBoardFetcher
from job_aggregator.fetching.ats_boards.greenhouse_board_fetcher import GreenhouseBoardFetcher
from job_aggregator.fetching.ats_boards.lever_board_fetcher import LeverBoardFetcher
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.registry.source_entry import SourceEntry
from tests.conftest import FIXTURES

# Accept every location and title so the contract (field mapping) is tested on real payloads.
EVERYTHING = SearchConfig(keywords=[], locations=["us", "ny", "remote", "european union", "spain"],
                          min_salary_lpa=0, max_required_yoe=10, max_job_age_days=30)


def _http(app_settings, routes):
    def handler(request):
        for fragment, response in routes.items():
            if fragment in str(request.url):
                return response
        return httpx.Response(404, json={"error": "not found"})

    return PoliteHttpClient(app_settings.fetching, transport=httpx.MockTransport(handler), sleep=lambda s: None)


def _payload(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _source(provider, companies):
    return SourceEntry(id=provider, name=provider, fetch_method="ats_board", enabled=True,
                       settings={"provider": provider, "companies": companies, "location_words": []})


def test_greenhouse_contract(app_settings):
    http = _http(app_settings, {"boards/twilio": httpx.Response(200, json=_payload("greenhouse_board.json"))})
    result = GreenhouseBoardFetcher(http).fetch(_source("greenhouse", ["twilio"]), EVERYTHING)
    job = result.listings[0]
    assert job.title == "Account Executive 4" and job.company == "Twilio"
    assert job.apply_url == "https://job-boards.greenhouse.io/twilio/jobs/8249615"
    assert job.location == "Remote - US" and job.apply_url_kind == "employer"
    assert result.status is SourceStatus.SUCCEEDED


def test_lever_contract(app_settings):
    http = _http(app_settings, {"postings/spotify": httpx.Response(200, json=_payload("lever_postings.json"))})
    result = LeverBoardFetcher(http).fetch(_source("lever", ["spotify"]), EVERYTHING)
    job = result.listings[0]
    assert job.title == "Account Executive - Commercial, Spotify Technology"
    assert job.location == "New York, NY" and job.employment_type == "Permanent"
    assert job.apply_url.endswith("/apply")


def test_ashby_contract(app_settings):
    http = _http(app_settings, {"job-board/ashby": httpx.Response(200, json=_payload("ashby_board.json"))})
    result = AshbyBoardFetcher(http).fetch(_source("ashby", ["ashby"]), EVERYTHING)
    job = result.listings[0]
    assert job.title == "Engineering Manager - EU"
    assert job.location.startswith("Remote - European Union") and job.is_remote
    assert job.salary_text.startswith("€150K")


def test_india_filter_keyword_filter_and_missing_board(app_settings):
    board = {"jobs": [
        {"id": 1, "title": "Java Developer", "absolute_url": "https://gh/1", "location": {"name": "Pune, India"}},
        {"id": 2, "title": "Java Developer", "absolute_url": "https://gh/2", "location": {"name": "Austin, TX"}},
        {"id": 3, "title": "Sales Lead", "absolute_url": "https://gh/3", "location": {"name": "Bengaluru, India"}},
    ]}
    http = _http(app_settings, {"boards/acme": httpx.Response(200, json=board)})
    criteria = SearchConfig(keywords=["java"], locations=["Pune"], min_salary_lpa=0, max_required_yoe=3,
                            max_job_age_days=30)
    source = SourceEntry(id="greenhouse", name="g", fetch_method="ats_board", enabled=True,
                         settings={"provider": "greenhouse", "companies": ["acme", "gone"]})
    result = GreenhouseBoardFetcher(http).fetch(source, criteria)
    assert [job.apply_url for job in result.listings] == ["https://gh/1"]
    assert result.status is SourceStatus.PARTIAL and "gone" in result.message
