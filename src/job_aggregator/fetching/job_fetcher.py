"""The interface every source fetcher implements."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from job_aggregator.domain.models import FetchResult, SearchConfig
from job_aggregator.registry.source_entry import SourceEntry


@runtime_checkable
class JobFetcher(Protocol):
    """Fetch raw listings for one registry entry.

    Implementations return listings in the common raw shape and may raise `SourceBlockedError`,
    `SourceTimeoutError` or any other error; `fetch_source_safely` turns errors into a recorded status.
    """

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult: ...
