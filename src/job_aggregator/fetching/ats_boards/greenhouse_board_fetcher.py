"""Greenhouse public job board API: boards-api.greenhouse.io/v1/boards/{company}/jobs."""

from __future__ import annotations

import html
from datetime import date

from job_aggregator.domain.models import RawListing
from job_aggregator.fetching.ats_boards.ats_board_fetcher import AtsBoardFetcher


class GreenhouseBoardFetcher(AtsBoardFetcher):
    def board_url(self, company: str) -> str:
        return f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"

    def jobs_in_payload(self, payload: object) -> list[dict]:
        return list(payload.get("jobs") or []) if isinstance(payload, dict) else []

    def job_to_listing(self, job: dict, company: str, source_id: str) -> RawListing:
        published = (job.get("first_published") or job.get("updated_at") or "")[:10]
        location = (job.get("location") or {}).get("name")
        return RawListing(
            source_id=source_id,
            title=job.get("title") or "",
            company=job.get("company_name") or company,
            apply_url=job.get("absolute_url") or "",
            source_url=job.get("absolute_url"),
            external_id=str(job.get("id")) if job.get("id") is not None else None,
            location=location,
            description=html.unescape(job.get("content") or ""),
            posted_at=date.fromisoformat(published) if published else None,
            is_remote=True if location and "remote" in location.lower() else None,
            apply_url_kind="employer",
        )
