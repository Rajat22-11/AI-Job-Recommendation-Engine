import httpx
import pytest

from job_aggregator.domain.errors import InvalidRegistryError, SourceBlockedError
from job_aggregator.domain.models import FetchResult, RawListing, SourceStatus
from job_aggregator.fetching.fetch_source_safely import fetch_source_safely
from job_aggregator.fetching.fetcher_factory import FetcherFactory, dispatch_by_provider
from job_aggregator.fetching.job_fetcher import JobFetcher
from job_aggregator.fetching.polite_http_client import PoliteHttpClient, TransientFetchError
from job_aggregator.registry.source_entry import SourceEntry

SOURCE = SourceEntry(id="himalayas", name="Himalayas", fetch_method="open_api", enabled=True,
                     settings={"provider": "himalayas"})


class FakeFetcher:
    def __init__(self, listings=None, error=None):
        self.listings, self.error, self.calls = listings or [], error, 0

    def fetch(self, source, search_config):
        self.calls += 1
        if self.error:
            raise self.error
        return FetchResult(source_id=source.id, status=SourceStatus.SUCCEEDED, listings=self.listings)


def _client(app_settings, handler, sleeps=None):
    sleeps = sleeps if sleeps is not None else []
    return PoliteHttpClient(app_settings.fetching, transport=httpx.MockTransport(handler), sleep=sleeps.append)


def test_fake_fetcher_satisfies_interface():
    assert isinstance(FakeFetcher(), JobFetcher)


def test_transient_error_recovers(app_settings):
    responses = iter([httpx.Response(503), httpx.Response(200, json={"jobs": [1]})])
    sleeps = []
    client = _client(app_settings, lambda request: next(responses), sleeps)
    assert client.get_json("https://api.example/jobs", "himalayas") == {"jobs": [1]}
    assert app_settings.fetching.retry_backoff_seconds in sleeps


def test_retries_exhausted_raises_and_stops(app_settings):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(502)

    client = _client(app_settings, handler)
    with pytest.raises(TransientFetchError):
        client.get_json("https://api.example/jobs", "himalayas")
    assert len(calls) == app_settings.fetching.max_retries + 1


@pytest.mark.parametrize(
    "response",
    [httpx.Response(403, text="Forbidden"),
     httpx.Response(200, headers={"content-type": "text/html"}, text="<h1>Please verify you are human</h1>")],
)
def test_login_wall_or_challenge_recorded_as_blocked(app_settings, response):
    client = _client(app_settings, lambda request: response)
    with pytest.raises(SourceBlockedError):
        client.get("https://board.example/jobs", "glassdoor")


def test_redirect_to_login_is_blocked_without_retry(app_settings):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/jobs":
            return httpx.Response(302, headers={"location": "https://board.example/login?next=/jobs"})
        return httpx.Response(200, text="<form>login</form>", headers={"content-type": "text/html"})

    with pytest.raises(SourceBlockedError, match="login"):
        _client(app_settings, handler).get("https://board.example/jobs", "wellfound")
    assert calls == ["/jobs", "/login"]


def test_pacing_waits_between_requests_to_same_host(app_settings):
    sleeps = []
    client = _client(app_settings, lambda request: httpx.Response(200, json={}), sleeps)
    client.get_json("https://api.example/a", "s")
    client.get_json("https://api.example/b", "s")
    assert sleeps and sleeps[-1] <= app_settings.fetching.pacing_seconds


def test_one_failing_source_does_not_stop_the_next(search_config):
    failing = FakeFetcher(error=RuntimeError("boom"))
    blocked = FakeFetcher(error=SourceBlockedError("glassdoor", "HTTP 403"))
    working = FakeFetcher([RawListing(source_id="himalayas", title="t", company="c", apply_url="https://x")])
    results = [fetch_source_safely(f, SOURCE, search_config, 100) for f in (failing, blocked, working)]
    assert [r.status for r in results] == [SourceStatus.FAILED, SourceStatus.BLOCKED, SourceStatus.SUCCEEDED]
    assert "boom" in results[0].message
    assert len(results[2].listings) == 1


def test_listing_cap_applied(search_config):
    listings = [RawListing(source_id="himalayas", title=f"t{i}", company="c", apply_url="https://x") for i in range(5)]
    result = fetch_source_safely(FakeFetcher(listings), SOURCE, search_config, 3)
    assert len(result.listings) == 3 and "capped" in result.message


def test_factory_resolves_by_lookup_table_and_rejects_unknown():
    himalayas = FakeFetcher()
    factory = FetcherFactory({"open_api": dispatch_by_provider({"himalayas": himalayas})})
    assert factory.fetcher_for(SOURCE) is himalayas
    with pytest.raises(InvalidRegistryError, match="no fetcher"):
        factory.fetcher_for(SourceEntry(id="x", name="x", fetch_method="rss_feed", enabled=True))
    with pytest.raises(InvalidRegistryError, match="unknown provider"):
        factory.fetcher_for(SourceEntry(id="y", name="y", fetch_method="open_api", enabled=True,
                                        settings={"provider": "nope"}))


def test_new_method_resolves_without_changing_factory_logic():
    rss = FakeFetcher()
    factory = FetcherFactory({"rss_feed": lambda source: rss})
    assert factory.fetcher_for(SourceEntry(id="x", name="x", fetch_method="rss_feed", enabled=True)) is rss
