"""Remotive (remotive.com) public API.

Remotive asks for at most about four calls a day and publishes jobs with a 24-hour delay. The fetcher
makes one call per run and skips the call once the configured daily cap is reached, counting calls
already made today from earlier runs. Listings keep Remotive's URL and name for attribution.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from job_aggregator.domain.models import FetchResult, RawListing, SearchConfig, SourceStatus
from job_aggregator.fetching.keyword_matching import DEFAULT_MATCHER, KeywordMatcher, matches_any_keyword
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.registry.source_entry import SourceEntry

API_URL = "https://remotive.com/api/remote-jobs"

CallsTodayLookup = Callable[[str], int]
"""Returns how many calls were already made to this source today (UTC), across all earlier runs."""


def remotive_job_to_listing(job: dict, source_id: str) -> RawListing:
    published = (job.get("publication_date") or "")[:10]
    region = job.get("candidate_required_location") or "Worldwide"
    return RawListing(
        source_id=source_id,
        title=job.get("title") or "",
        company=job.get("company_name") or "",
        apply_url=job.get("url") or "",
        source_url=job.get("url"),
        external_id=str(job["id"]) if job.get("id") is not None else None,
        location=f"Remote ({region})",
        description=job.get("description"),
        salary_text=job.get("salary") or None,
        employment_type=job.get("job_type"),
        skills=list(job.get("tags") or []),
        posted_at=date.fromisoformat(published) if published else None,
        is_remote=True,
        apply_url_kind="board",
    )


class RemotiveFetcher:
    def __init__(self, http: PoliteHttpClient, calls_made_today: CallsTodayLookup,
                 matcher: KeywordMatcher = DEFAULT_MATCHER) -> None:
        self._http = http
        self._calls_made_today = calls_made_today
        self._matcher = matcher

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult:
        cap = int(source.setting("max_calls_per_day", 4))
        made = self._calls_made_today(source.id)
        if made >= cap:
            return FetchResult(source_id=source.id, status=SourceStatus.SKIPPED,
                               message=f"daily call cap reached ({made}/{cap}); Remotive allows about 4 calls a day")
        params = {"category": source.setting("category", "software-dev"), "limit": source.setting("limit", 150)}
        payload = self._http.get_json(API_URL, source.id, params)
        jobs = (payload.get("jobs") or []) if isinstance(payload, dict) else []
        listings = [
            remotive_job_to_listing(job, source.id)
            for job in jobs
            if matches_any_keyword([job.get("title"), " ".join(job.get("tags") or [])], search_config.keywords,
                                   self._matcher)
        ]
        return FetchResult(source_id=source.id, status=SourceStatus.SUCCEEDED, listings=listings,
                           message=f"call {made + 1}/{cap} today; {len(jobs)} jobs, {len(listings)} match keywords; "
                                   "Remotive data is delayed by 24 hours")
