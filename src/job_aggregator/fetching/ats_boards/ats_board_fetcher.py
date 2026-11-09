"""Shared logic for public company applicant-tracking boards (Greenhouse, Lever, Ashby).

Each provider lists every job of one company; this keeps the jobs located in India (or matching the
owner's locations) whose title matches a search keyword. A missing board (404) is skipped and the
source is reported as partial instead of failing.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod

import httpx

from job_aggregator.domain.models import FetchResult, RawListing, SearchConfig, SourceStatus
from job_aggregator.fetching.keyword_matching import DEFAULT_MATCHER, KeywordMatcher, matches_any_keyword
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.registry.source_entry import SourceEntry

logger = logging.getLogger(__name__)
DEFAULT_LOCATION_WORDS = ("india",)


def location_is_wanted(location: str | None, wanted_words: list[str]) -> bool:
    text = (location or "").lower()
    return any(re.search(rf"(?<!\w){re.escape(word.lower())}(?!\w)", text) for word in wanted_words if word)


class AtsBoardFetcher(ABC):
    """Template for one ATS provider: subclasses only know the URL and how to read one job."""

    def __init__(self, http: PoliteHttpClient, matcher: KeywordMatcher = DEFAULT_MATCHER) -> None:
        self._http = http
        self._matcher = matcher

    @abstractmethod
    def board_url(self, company: str) -> str: ...

    @abstractmethod
    def jobs_in_payload(self, payload: object) -> list[dict]: ...

    @abstractmethod
    def job_to_listing(self, job: dict, company: str, source_id: str) -> RawListing: ...

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult:
        wanted_locations = [*source.setting("location_words", DEFAULT_LOCATION_WORDS), *search_config.locations]
        listings: list[RawListing] = []
        missing: list[str] = []
        companies = list(source.setting("companies", []))
        for company in companies:
            try:
                payload = self._http.get_json(self.board_url(company), source.id)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    missing.append(company)
                    continue
                raise
            for job in self.jobs_in_payload(payload):
                listing = self.job_to_listing(job, company, source.id)
                if location_is_wanted(listing.location, wanted_locations) and matches_any_keyword(
                    [listing.title], search_config.keywords, self._matcher
                ):
                    listings.append(listing)
        status = SourceStatus.PARTIAL if missing and len(missing) < len(companies) else SourceStatus.SUCCEEDED
        if companies and len(missing) == len(companies):
            status = SourceStatus.FAILED
        message = f"{len(companies)} board(s), {len(listings)} matching jobs"
        if missing:
            message += f"; board not found: {', '.join(missing)}"
        return FetchResult(source_id=source.id, status=status, listings=listings, message=message)
