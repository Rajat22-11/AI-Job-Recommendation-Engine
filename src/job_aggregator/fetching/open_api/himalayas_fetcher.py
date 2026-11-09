"""Himalayas (himalayas.app) public jobs search API, filtered to India.

Attribution: each listing keeps Himalayas as its source and its original Himalayas URL.
"""

from __future__ import annotations

from datetime import UTC, datetime

from job_aggregator.domain.models import FetchResult, RawListing, SearchConfig, SourceStatus
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.registry.source_entry import SourceEntry

SEARCH_URL = "https://himalayas.app/jobs/api/search"
PAGE_SIZE = 20


def himalayas_location(restrictions: list[str] | None) -> str:
    if not restrictions:
        return "Remote (Worldwide)"
    return f"Remote ({', '.join(restrictions)})"


def himalayas_salary_text(job: dict) -> str | None:
    low, high = job.get("minSalary"), job.get("maxSalary")
    if low is None and high is None:
        return None
    currency = job.get("currency") or ""
    period = job.get("salaryPeriod") or "annual"
    amounts = " - ".join(f"{value:,}" for value in (low, high) if value is not None)
    suffix = {"annual": "per year", "month": "per month", "monthly": "per month", "hour": "per hour",
              "hourly": "per hour"}.get(period, period)
    return f"{currency} {amounts} {suffix}".strip()


def himalayas_job_to_listing(job: dict, source_id: str) -> RawListing:
    published = job.get("pubDate")
    return RawListing(
        source_id=source_id,
        title=job.get("title") or "",
        company=job.get("companyName") or "",
        apply_url=job.get("applicationLink") or job.get("guid") or "",
        source_url=job.get("guid") or job.get("applicationLink"),
        external_id=job.get("guid"),
        location=himalayas_location(job.get("locationRestrictions")),
        description=job.get("description") or job.get("excerpt"),
        salary_text=himalayas_salary_text(job),
        employment_type=job.get("employmentType"),
        experience_text=" ".join(job.get("seniority") or []) or None,
        skills=[c.replace("-", " ") for c in (job.get("categories") or [])[:8]],
        posted_at=datetime.fromtimestamp(published, UTC).date() if published else None,
        is_remote=True,
        apply_url_kind="board",
    )


class HimalayasFetcher:
    def __init__(self, http: PoliteHttpClient) -> None:
        self._http = http

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult:
        country = source.setting("country", "India")
        max_pages = int(source.setting("max_pages", 3))
        keywords = search_config.keywords[: int(source.setting("max_keywords", 4))] or [""]
        listings: dict[str, RawListing] = {}
        calls = 0
        for keyword in keywords:
            for page in range(1, max_pages + 1):
                payload = self._http.get_json(SEARCH_URL, source.id, {"q": keyword, "country": country, "page": page})
                calls += 1
                jobs = (payload.get("jobs") or []) if isinstance(payload, dict) else []
                for job in jobs:
                    listing = himalayas_job_to_listing(job, source.id)
                    listings.setdefault(listing.source_url or listing.apply_url, listing)
                if len(jobs) < PAGE_SIZE:
                    break
        return FetchResult(source_id=source.id, status=SourceStatus.SUCCEEDED, listings=list(listings.values()),
                           message=f"{calls} search calls for {len(keywords)} keyword(s) in {country}")
