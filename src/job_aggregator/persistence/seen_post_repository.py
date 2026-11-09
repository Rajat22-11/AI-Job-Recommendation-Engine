"""LinkedIn posts already processed (`linkedin_seen_posts`, created by migration 002)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from job_aggregator.persistence.database_client import DatabaseClient

PostOutcome = Literal["job_created", "ignored", "unparsed"]
TABLE = "linkedin_seen_posts"
logger = logging.getLogger(__name__)


class SeenPostRepository:
    def __init__(self, database: DatabaseClient) -> None:
        self._db = database

    def find_seen_post_urls(self, post_urls: list[str]) -> set[str]:
        if not post_urls:
            return set()
        try:
            rows = self._db.select(TABLE, "post_url", [("post_url", "in", list(dict.fromkeys(post_urls)))])
        except Exception as error:  # noqa: BLE001 - only the missing-table case is tolerated
            self._tolerate_missing_table(error)
            return set()
        return {row["post_url"] for row in rows}

    def record_post(
        self, post_url: str, source_id: str, outcome: PostOutcome, seen_at: datetime,
        job_id: str | None = None, note: str | None = None,
    ) -> None:
        try:
            self._db.upsert(TABLE, [{
                "post_url": post_url, "source_id": source_id, "outcome": outcome, "job_id": job_id,
                "note": (note or "")[:1000] or None, "seen_at": seen_at.isoformat(),
            }], on_conflict="post_url", ignore_duplicates=True)
        except Exception as error:  # noqa: BLE001
            self._tolerate_missing_table(error)

    @staticmethod
    def _tolerate_missing_table(error: Exception) -> None:
        """Until migration 002 is applied the table is absent: posts are re-read each run, and the job's own
        dedupe key still prevents duplicate jobs. Any other database error is raised as before."""
        if "PGRST205" not in str(error) and TABLE not in str(error):
            raise error
        logger.warning("table %s is missing (apply migrations/002); LinkedIn posts will be re-read each run", TABLE)
