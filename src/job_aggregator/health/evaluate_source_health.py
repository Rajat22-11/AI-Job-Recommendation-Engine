"""Spot sources that silently stop returning jobs, and runs that never happened."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from job_aggregator.domain.models import SourceStatus
from job_aggregator.settings.app_settings import HealthSettings

MIN_BASELINE_FOR_LOW_RATIO = 3.0
"""A source must average at least this many listings before a 'far below average' alert makes sense."""


@dataclass(frozen=True)
class SourceHealth:
    empty_run_streak: int
    alert: str | None


def evaluate_source_health(
    source_id: str,
    status: SourceStatus,
    jobs_found: int,
    previous_runs: list[dict],
    previous_empty_streak: int,
    settings: HealthSettings,
) -> SourceHealth:
    """Return the updated empty-run streak and an alert message when the source looks unhealthy.

    `previous_runs` are earlier `source_runs` rows for this source, newest first.
    Skipped runs neither extend nor reset the streak.
    """
    if status is SourceStatus.SKIPPED:
        return SourceHealth(previous_empty_streak, None)

    streak = previous_empty_streak + 1 if jobs_found == 0 else 0
    if streak >= settings.consecutive_empty_runs_alert:
        return SourceHealth(streak, f"{source_id} returned no jobs for {streak} runs in a row")

    counted = [row for row in previous_runs if row.get("status") != "skipped"][: settings.baseline_runs]
    if counted and jobs_found > 0:
        average = sum(int(row.get("jobs_found") or 0) for row in counted) / len(counted)
        if average >= MIN_BASELINE_FOR_LOW_RATIO and jobs_found < average * settings.low_ratio_alert:
            return SourceHealth(streak, f"{source_id} returned {jobs_found} jobs, far below its recent average of "
                                        f"{average:.0f}")
    return SourceHealth(streak, None)


def detect_missed_run(latest_run_started_at: datetime | None, now: datetime, missed_run_hours: float) -> str | None:
    """Alert text when no run has been recorded within the configured hours."""
    if latest_run_started_at is None:
        return "No pipeline run has ever been recorded"
    age = now - latest_run_started_at
    if age > timedelta(hours=missed_run_hours):
        hours = age.total_seconds() / 3600
        return f"No pipeline run recorded for {hours:.0f} hours (limit {missed_run_hours:g}); the scheduler may be down"
    return None
