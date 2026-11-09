"""Store jobs exactly once by dedupe key, link every source, and retire stale jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from job_aggregator.domain.models import NormalizedJob
from job_aggregator.persistence.database_client import DatabaseClient

LOOKUP_CHUNK = 100
JOB_COLUMNS = (
    "dedupe_key", "title", "company", "location", "location_bucket", "work_mode", "employment_type", "role_track",
    "min_yoe", "max_yoe", "salary_text", "salary_min_lpa", "salary_max_lpa", "salary_meets_min", "skills",
    "summary", "apply_url", "posted_at", "fit_score", "fit_reason", "apply_url_kind",
)


@dataclass
class StoreJobsResult:
    """Which dedupe keys were new in this batch and which were already stored."""

    new_keys: list[str] = field(default_factory=list)
    seen_again_keys: list[str] = field(default_factory=list)
    new_count_by_source: dict[str, int] = field(default_factory=dict)


class JobRepository:
    def __init__(self, database: DatabaseClient) -> None:
        self._db = database

    def find_existing_keys(self, dedupe_keys: list[str]) -> dict[str, str]:
        """Return dedupe key -> job id for keys already stored."""
        found: dict[str, str] = {}
        unique_keys = list(dict.fromkeys(dedupe_keys))
        for start in range(0, len(unique_keys), LOOKUP_CHUNK):
            chunk = unique_keys[start:start + LOOKUP_CHUNK]
            rows = self._db.select("jobs", "id,dedupe_key", [("dedupe_key", "in", chunk)])
            found.update({row["dedupe_key"]: row["id"] for row in rows})
        return found

    def store_jobs(self, jobs: list[NormalizedJob], seen_at: datetime) -> StoreJobsResult:
        """Insert new jobs, refresh last-seen for known ones, and link each job to every source it came from.

        Safe to repeat: inserts ignore keys that already exist and links are keyed by URL.
        """
        result = StoreJobsResult()
        if not jobs:
            return result
        first_by_key: dict[str, NormalizedJob] = {}
        for job in jobs:
            first_by_key.setdefault(job.dedupe_key, job)

        existing = self.find_existing_keys(list(first_by_key))
        new_jobs = [job for key, job in first_by_key.items() if key not in existing]
        result.seen_again_keys = [key for key in first_by_key if key in existing]
        timestamp = seen_at.isoformat()

        if new_jobs:
            rows = [self._job_row(job, timestamp) for job in new_jobs]
            self._db.upsert("jobs", rows, on_conflict="dedupe_key", ignore_duplicates=True)
        if result.seen_again_keys:
            for start in range(0, len(result.seen_again_keys), LOOKUP_CHUNK):
                chunk = result.seen_again_keys[start:start + LOOKUP_CHUNK]
                self._db.update("jobs", {"last_seen_at": timestamp, "is_active": True}, [("dedupe_key", "in", chunk)])

        ids_by_key = {**existing, **self.find_existing_keys([job.dedupe_key for job in new_jobs])}
        result.new_keys = [job.dedupe_key for job in new_jobs if job.dedupe_key in ids_by_key]
        for job in new_jobs:
            result.new_count_by_source[job.source_id] = result.new_count_by_source.get(job.source_id, 0) + 1

        links: dict[str, dict] = {}
        for job in jobs:
            job_id = ids_by_key.get(job.dedupe_key)
            if job_id:
                links[job.source_url] = {
                    "job_id": job_id, "source_id": job.source_id, "url": job.source_url,
                    "external_id": job.external_id, "scraped_at": timestamp,
                }
        if links:
            self._db.upsert("job_sources", list(links.values()), on_conflict="url", ignore_duplicates=True)
        return result

    def job_ids_for_keys(self, dedupe_keys: list[str]) -> dict[str, str]:
        return self.find_existing_keys(dedupe_keys)

    def retire_stale_jobs(self, now: datetime, max_job_age_days: int, stale_after_days_unseen: int) -> int:
        """Mark jobs inactive when unseen for too long or older than the maximum age. Rows are kept."""
        unseen_cutoff = (now - timedelta(days=stale_after_days_unseen)).isoformat()
        age_cutoff = (now - timedelta(days=max_job_age_days)).date().isoformat()
        retired = self._db.update(
            "jobs", {"is_active": False}, [("is_active", "eq", True), ("last_seen_at", "lt", unseen_cutoff)]
        )
        retired += self._db.update(
            "jobs", {"is_active": False}, [("is_active", "eq", True), ("posted_at", "lt", age_cutoff)]
        )
        return len({row.get("id") for row in retired})

    @staticmethod
    def _job_row(job: NormalizedJob, timestamp: str) -> dict:
        data = job.model_dump(include=set(JOB_COLUMNS), mode="json")
        data.update({"is_active": True, "first_seen_at": timestamp, "last_seen_at": timestamp})
        return data
