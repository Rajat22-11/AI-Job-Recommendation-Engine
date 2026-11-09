"""Map each registry `fetch_method` to the fetcher that handles it, through a lookup table."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from job_aggregator.domain.errors import InvalidRegistryError
from job_aggregator.fetching.job_fetcher import JobFetcher
from job_aggregator.registry.source_entry import SourceEntry

FetcherBuilder = Callable[[SourceEntry], JobFetcher]


class FetcherFactory:
    """Resolves fetchers. Adding a fetch method means adding one entry to the `builders` table."""

    def __init__(self, builders: Mapping[str, FetcherBuilder]) -> None:
        self._builders = dict(builders)

    def fetcher_for(self, source: SourceEntry) -> JobFetcher:
        builder = self._builders.get(source.fetch_method)
        if builder is None:
            raise InvalidRegistryError(source.id, f"no fetcher for fetch method '{source.fetch_method}'")
        return builder(source)

    @property
    def supported_methods(self) -> set[str]:
        return set(self._builders)


def dispatch_by_provider(fetchers_by_provider: Mapping[str, JobFetcher], setting: str = "provider") -> FetcherBuilder:
    """Builder for methods (open_api, ats_board) whose concrete fetcher depends on a `provider` setting."""

    def build(source: SourceEntry) -> JobFetcher:
        provider = source.setting(setting)
        fetcher = fetchers_by_provider.get(provider)
        if fetcher is None:
            raise InvalidRegistryError(source.id, f"unknown {setting} '{provider}' for '{source.fetch_method}'")
        return fetcher

    return build
