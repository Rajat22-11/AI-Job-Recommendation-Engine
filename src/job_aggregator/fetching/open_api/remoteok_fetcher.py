"""Remote OK (remoteok.com) public API.

The first element of the response is a legal notice, not a job, and is skipped. Remote OK requires a
link back and credit: listings keep the original Remote OK URL and the source name.
"""

from __future__ import annotations

from datetime import date

from job_aggregator.domain.models import FetchResult, RawListing, SearchConfig, SourceStatus
from job_aggregator.fetching.keyword_matching import DEFAULT_MATCHER, KeywordMatcher, matches_any_keyword
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.registry.source_entry import SourceEntry

API_URL = "https://remoteok.com/api"


def is_remoteok_job(item: object) -> bool:
    return isinstance(item, dict) and "legal" not in item and bool(item.get("position"))


def remoteok_salary_text(item: dict) -> str | None:
    low, high = item.get("salary_min") or 0, item.get("salary_max") or 0
    if not low and not high:
        return None
    return " - ".join(f"${value:,}" for value in (low, high) if value) + " per year"


def remoteok_item_to_listing(item: dict, source_id: str) -> RawListing:
    posted = (item.get("date") or "")[:10]
    return RawListing(
        source_id=source_id,
        title=item.get("position") or "",
        company=item.get("company") or "",
        apply_url=item.get("apply_url") or item.get("url") or "",
        source_url=item.get("url") or item.get("apply_url"),
        external_id=str(item.get("id")) if item.get("id") is not None else None,
        location=item.get("location") or "Remote",
        description=item.get("description"),
        salary_text=remoteok_salary_text(item),
        skills=list(item.get("tags") or []),
        posted_at=date.fromisoformat(posted) if posted else None,
        is_remote=True,
        apply_url_kind="board",
    )


class RemoteOkFetcher:
    def __init__(self, http: PoliteHttpClient, matcher: KeywordMatcher = DEFAULT_MATCHER) -> None:
        self._http = http
        self._matcher = matcher

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult:
        payload = self._http.get_json(API_URL, source.id)
        items = [item for item in (payload if isinstance(payload, list) else []) if is_remoteok_job(item)]
        listings = [
            remoteok_item_to_listing(item, source.id)
            for item in items
            if matches_any_keyword([item.get("position"), " ".join(item.get("tags") or [])], search_config.keywords,
                                   self._matcher)
        ]
        return FetchResult(source_id=source.id, status=SourceStatus.SUCCEEDED, listings=listings,
                           message=f"{len(items)} jobs, {len(listings)} match keywords (source: Remote OK)")
