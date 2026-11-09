"""Run and per-source run records (`runs`, `source_runs`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from job_aggregator.domain.models import RunStatus, SourceRunRecord, SourceStatus
from job_aggregator.persistence.database_client import DatabaseClient

DATABASE_SOURCE_STATUS: dict[SourceStatus, str] = {
    SourceStatus.SUCCEEDED: "ok",
    SourceStatus.PARTIAL: "partial",
    SourceStatus.FAILED: "error",
    SourceStatus.BLOCKED: "error",  # refined by block kind in database_source_status
    SourceStatus.SKIPPED: "skipped",
}
"""Domain status -> value allowed by `source_runs_status_check` (see docs/database-notes.md)."""


def database_source_status(status: SourceStatus, block_kind: str | None = None) -> str:
    """Map a domain status to the database value.

    The UI shows "Log in to X in Chrome" for `needs_login` and `captcha`, so only a real sign-in wall
    and a challenge page use them. A block by IP or HTTP status is `error`, with the reason in the message.
    """
    if status is SourceStatus.BLOCKED:
        return {"login": "needs_login", "challenge": "captcha"}.get(block_kind or "", "error")
    return DATABASE_SOURCE_STATUS[status]


class RunRepository:
    def __init__(self, database: DatabaseClient) -> None:
        self._db = database

    def start_run(self, run_id: str, trigger_id: str, started_at: datetime, config_snapshot: dict[str, Any]) -> None:
        self._db.insert("runs", [{
            "run_id": run_id, "trigger_id": trigger_id, "started_at": started_at.isoformat(),
            "status": RunStatus.RUNNING.value, "config_snapshot": config_snapshot,
        }])

    def finish_run(self, run_id: str, status: RunStatus, finished_at: datetime, summary: str, notified: bool) -> None:
        self._db.update("runs", {
            "status": status.value, "finished_at": finished_at.isoformat(), "summary": summary, "notified": notified,
        }, [("run_id", "eq", run_id)])

    def record_source_run(self, run_id: str, record: SourceRunRecord) -> None:
        self._db.insert("source_runs", [{
            "run_id": run_id,
            "source_id": record.source_id,
            "status": database_source_status(record.status, record.block_kind),
            "jobs_found": record.jobs_found,
            "jobs_new": record.jobs_new,
            "message": record.message[:2000],
            "started_at": record.started_at.isoformat(),
            "finished_at": record.finished_at.isoformat() if record.finished_at else None,
        }])

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        rows = self._db.select("runs", "*", [("run_id", "eq", run_id)], limit=1)
        return rows[0] if rows else None

    def latest_run(self) -> dict[str, Any] | None:
        rows = self._db.select("runs", "*", order_by="started_at", descending=True, limit=1)
        return rows[0] if rows else None

    def running_runs(self) -> list[dict[str, Any]]:
        return self._db.select("runs", "*", [("status", "eq", RunStatus.RUNNING.value)], order_by="started_at",
                               descending=True)

    def mark_interrupted(self, run_id: str, finished_at: datetime, reason: str) -> None:
        self._db.update("runs", {
            "status": RunStatus.INTERRUPTED.value, "finished_at": finished_at.isoformat(), "summary": reason,
        }, [("run_id", "eq", run_id), ("status", "eq", RunStatus.RUNNING.value)])

    def count_source_calls_today(self, source_id: str, now: datetime) -> int:
        """Runs today (UTC) in which this source was actually called (not skipped)."""
        start_of_day = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        rows = self._db.select("source_runs", "status", [("source_id", "eq", source_id),
                                                          ("started_at", "gte", start_of_day)])
        return sum(1 for row in rows if row.get("status") != "skipped")

    def last_successful_source_run_at(self, source_id: str) -> datetime | None:
        rows = self._db.select("source_runs", "started_at", [("source_id", "eq", source_id),
                                                              ("status", "in", ["ok", "partial"])],
                               order_by="started_at", descending=True, limit=1)
        return datetime.fromisoformat(rows[0]["started_at"]) if rows else None

    def recent_source_runs(self, source_id: str, limit: int) -> list[dict[str, Any]]:
        """Newest-first `source_runs` rows for one source."""
        return self._db.select("source_runs", "status,jobs_found,jobs_new,started_at",
                               [("source_id", "eq", source_id)], order_by="started_at", descending=True, limit=limit)
