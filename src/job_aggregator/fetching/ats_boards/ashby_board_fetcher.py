"""Ashby public job board API: api.ashbyhq.com/posting-api/job-board/{company}."""

from __future__ import annotations

from datetime import date

from job_aggregator.domain.models import RawListing
from job_aggregator.fetching.ats_boards.ats_board_fetcher import AtsBoardFetcher


class AshbyBoardFetcher(AtsBoardFetcher):
    def board_url(self, company: str) -> str:
        return f"https://api.ashbyhq.com/posting-api/job-board/{company}?includeCompensation=true"

    def jobs_in_payload(self, payload: object) -> list[dict]:
        if not isinstance(payload, dict):
            return []
        return [job for job in payload.get("jobs") or [] if job.get("isListed", True)]

    def job_to_listing(self, job: dict, company: str, source_id: str) -> RawListing:
        locations = [job.get("location")] + [s.get("location") for s in job.get("secondaryLocations") or []]
        location = " / ".join(loc for loc in locations if loc) or None
        if job.get("isRemote") and location and "remote" not in location.lower():
            location = f"{location} (Remote)"
        published = (job.get("publishedAt") or "")[:10]
        compensation = (job.get("compensation") or {}).get("compensationTierSummary")
        return RawListing(
            source_id=source_id,
            title=job.get("title") or "",
            company=company,
            apply_url=job.get("applyUrl") or job.get("jobUrl") or "",
            source_url=job.get("jobUrl") or job.get("applyUrl"),
            external_id=job.get("id"),
            location=location,
            description=job.get("descriptionPlain") or job.get("descriptionHtml"),
            salary_text=compensation,
            employment_type=job.get("employmentType"),
            posted_at=date.fromisoformat(published) if published else None,
            is_remote=bool(job.get("isRemote")) or None,
            apply_url_kind="employer",
        )
