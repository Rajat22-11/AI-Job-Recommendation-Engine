"""Lever public postings API: api.lever.co/v0/postings/{company}?mode=json."""

from __future__ import annotations

from datetime import UTC, datetime

from job_aggregator.domain.models import RawListing
from job_aggregator.fetching.ats_boards.ats_board_fetcher import AtsBoardFetcher


class LeverBoardFetcher(AtsBoardFetcher):
    def board_url(self, company: str) -> str:
        return f"https://api.lever.co/v0/postings/{company}?mode=json"

    def jobs_in_payload(self, payload: object) -> list[dict]:
        return list(payload) if isinstance(payload, list) else []

    def job_to_listing(self, job: dict, company: str, source_id: str) -> RawListing:
        categories = job.get("categories") or {}
        locations = categories.get("allLocations") or [categories.get("location")]
        location = " / ".join(loc for loc in locations if loc) or None
        if job.get("workplaceType") == "remote" and location and "remote" not in location.lower():
            location = f"{location} (Remote)"
        created = job.get("createdAt")
        return RawListing(
            source_id=source_id,
            title=job.get("text") or "",
            company=company,
            apply_url=job.get("applyUrl") or job.get("hostedUrl") or "",
            source_url=job.get("hostedUrl") or job.get("applyUrl"),
            external_id=job.get("id"),
            location=location,
            description=job.get("descriptionPlain") or job.get("description"),
            salary_text=job.get("additionalPlain") if "$" in (job.get("additionalPlain") or "") else None,
            employment_type=categories.get("commitment"),
            posted_at=datetime.fromtimestamp(int(created) / 1000, UTC).date() if created else None,
            is_remote=True if job.get("workplaceType") == "remote" else None,
            apply_url_kind="employer",
        )
