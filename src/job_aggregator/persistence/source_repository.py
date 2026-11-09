"""The `sources` table: registry sync and per-source health columns.

The UI owns what the owner edits: `enabled`, `name`, `base_url`, notes and login flag. The sync therefore
never changes those on an existing row; a new row is created from the registry entry. The registry owns
*how* a source is fetched, so the sync sets `access_method` (mapped to a value allowed by
`sources_access_method_check`, see docs/database-notes.md) on both new and existing rows. That also makes
the UI show "template not applicable" for sources that never use a URL template.
"""

from __future__ import annotations

from datetime import datetime

from job_aggregator.persistence.database_client import DatabaseClient
from job_aggregator.registry.source_entry import SourceEntry

ACCESS_METHOD_FOR_FETCH_METHOD: dict[str, str] = {
    "open_api": "api",
    "ats_board": "api",
    "jobspy_board": "connector",
    "apify_job_board": "api",
    "linkedin_profile_posts": "api",
    "rss_feed": "rss",
    "web_page": "public_scrape",
}
"""Fetch method -> value allowed by the live check constraint (auto, connector, public_scrape,
browser_session, api, rss). The UI treats connector, api and rss as "no URL template needed"."""


class SourceRepository:
    def __init__(self, database: DatabaseClient) -> None:
        self._db = database

    def sync_registry(self, entries: list[SourceEntry]) -> dict[str, int]:
        """Create missing rows and keep `access_method` current; the UI's edits are never overwritten."""
        ids = [entry.id for entry in entries]
        rows = self._db.select("sources", "id,access_method", [("id", "in", ids)]) if ids else []
        existing = {row["id"]: row for row in rows}
        created = updated = 0
        for entry in entries:
            access_method = ACCESS_METHOD_FOR_FETCH_METHOD.get(entry.fetch_method, "auto")
            row = existing.get(entry.id)
            if row is None:
                self._db.insert("sources", [{
                    "id": entry.id, "name": entry.name,
                    "base_url": entry.base_url or entry.setting("profile_url") or "",
                    "enabled": entry.enabled, "access_method": access_method,
                }])
                created += 1
            elif row.get("access_method") != access_method:
                self._db.update("sources", {"access_method": access_method}, [("id", "eq", entry.id)])
                updated += 1
        return {"created": created, "updated": updated}

    def enabled_source_ids(self) -> list[str]:
        """Every source the owner has enabled in the UI, whether or not this pipeline can fetch it."""
        return [row["id"] for row in self._db.select("sources", "id", [("enabled", "eq", True)])]

    def enabled_flags(self, source_ids: list[str]) -> dict[str, bool]:
        """The `enabled` flag as the owner set it in the UI, for the ids that exist."""
        if not source_ids:
            return {}
        rows = self._db.select("sources", "id,enabled", [("id", "in", source_ids)])
        return {row["id"]: bool(row["enabled"]) for row in rows}

    def health_columns(self, source_ids: list[str]) -> dict[str, dict]:
        if not source_ids:
            return {}
        rows = self._db.select("sources", "id,consecutive_empty_runs,last_success_at", [("id", "in", source_ids)])
        return {row["id"]: row for row in rows}

    def update_health(self, source_id: str, empty_run_streak: int, last_success_at: datetime | None) -> None:
        values: dict = {"consecutive_empty_runs": empty_run_streak}
        if last_success_at is not None:
            values["last_success_at"] = last_success_at.isoformat()
        self._db.update("sources", values, [("id", "eq", source_id)])
