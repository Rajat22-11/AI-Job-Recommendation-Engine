"""Start pipeline runs in the background, one at a time, and report their state.

- At most one active run: an in-process lock plus a check of `runs` for a recent row still marked running.
- A second start while a run is active returns the active run's id and starts nothing.
- After a finished run today, a repeat start follows `trigger.repeat_trigger_behaviour`
  (`return_finished` returns that run; `start_new` starts another). `force=True` always starts a new run.
- Runs started by the service carry a `service:` trigger prefix. On start-up, any of those still marked
  running belong to a dead process and are marked interrupted. Runs from the owner's PC are left alone
  unless they are older than `trigger.stale_running_minutes`.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from job_aggregator.domain.models import RunStatus, RunSummary
from job_aggregator.orchestration.daily_run_pipeline import RunOptions
from job_aggregator.persistence.run_repository import RunRepository
from job_aggregator.settings.app_settings import TriggerSettings

logger = logging.getLogger(__name__)
SERVICE_TRIGGER_PREFIX = "service:"
FINISHED_OK = {RunStatus.SUCCEEDED.value, RunStatus.PARTIAL.value}

PipelineRunner = Callable[[RunOptions], RunSummary]
ThreadStarter = Callable[[Callable[[], None]], None]


def start_daemon_thread(target: Callable[[], None]) -> None:
    threading.Thread(target=target, name="pipeline-run", daemon=True).start()


@dataclass
class StartOutcome:
    run_id: str
    started: bool
    state: str
    reason: str = ""


@dataclass
class _ActiveRun:
    run_id: str
    started_at: datetime
    done: threading.Event = field(default_factory=threading.Event)
    summary: RunSummary | None = None
    error: str | None = None


class RunManager:
    def __init__(
        self,
        run_pipeline: PipelineRunner,
        runs: RunRepository,
        settings: TriggerSettings,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        start_thread: ThreadStarter = start_daemon_thread,
        skip_methods: tuple[str, ...] = (),
    ) -> None:
        self._skip_methods = skip_methods
        self._run_pipeline = run_pipeline
        self._runs = runs
        self._settings = settings
        self._clock = clock
        self._start_thread = start_thread
        self._lock = threading.Lock()
        self._active: _ActiveRun | None = None
        self._finished: dict[str, _ActiveRun] = {}

    # ------------------------------------------------------------------ lifecycle

    def recover_interrupted_runs(self) -> list[str]:
        """Mark runs left 'running' by a previous service process (or stale ones) as interrupted."""
        now = self._clock()
        recovered = []
        for row in self._runs.running_runs():
            # Only this service's own runs: rows left by the old Claude routine or the PC are history.
            from_service = str(row.get("trigger_id") or "").startswith(SERVICE_TRIGGER_PREFIX)
            if from_service:
                self._runs.mark_interrupted(row["run_id"], now, "interrupted: the service restarted or the run "
                                                                "stopped reporting")
                recovered.append(row["run_id"])
        if recovered:
            logger.warning("marked %d abandoned run(s) as interrupted", len(recovered))
        return recovered

    def start(
        self, trigger_id: str = "trigger", force: bool = False, options: RunOptions | None = None
    ) -> StartOutcome:
        with self._lock:
            if self._active and not self._active.done.is_set():
                return StartOutcome(self._active.run_id, False, "running", "a run is already active")

            other = self._recent_running_row()
            if other:
                return StartOutcome(other["run_id"], False, "running", "a run started elsewhere is still running")

            if not force and self._settings.repeat_trigger_behaviour == "return_finished":
                finished = self._finished_today()
                if finished:
                    return StartOutcome(finished["run_id"], False, str(finished.get("status")),
                                        "today's run already finished; pass force to start another")

            run_id = str(uuid.uuid4())
            base = options or RunOptions()
            run_options = RunOptions(trigger_id=f"{SERVICE_TRIGGER_PREFIX}{trigger_id}", dry_run=base.dry_run,
                                     only_sources=base.only_sources, only_methods=base.only_methods,
                                     skip_methods=tuple({*base.skip_methods, *self._skip_methods}), run_id=run_id)
            active = _ActiveRun(run_id=run_id, started_at=self._clock())
            self._active = active
            self._start_thread(lambda: self._execute(active, run_options))
            return StartOutcome(run_id, True, "running")

    def status(self, run_id: str) -> dict[str, Any] | None:
        """State of a run: running, succeeded, partial, failed or interrupted (None when unknown)."""
        with self._lock:
            active = self._active if self._active and self._active.run_id == run_id else self._finished.get(run_id)
        if active and not active.done.is_set():
            return {"run_id": run_id, "state": "running", "started_at": active.started_at.isoformat()}

        row = self._runs.get_run(run_id)
        if row is None:
            if active and active.error:
                return {"run_id": run_id, "state": "failed", "error": active.error}
            return None
        state = str(row.get("status") or "unknown")
        if state == RunStatus.RUNNING.value and str(row.get("trigger_id") or "").startswith(SERVICE_TRIGGER_PREFIX):
            # Marked running in the database but not running in this process: its process died.
            self._runs.mark_interrupted(run_id, self._clock(), "interrupted: the service restarted during the run")
            state = RunStatus.INTERRUPTED.value
        result = {"run_id": run_id, "state": state, "started_at": row.get("started_at"),
                  "finished_at": row.get("finished_at"), "summary": row.get("summary")}
        if active and active.summary:
            result.update({"jobs_found": active.summary.jobs_found, "jobs_new": active.summary.jobs_new})
        return result

    @property
    def active_run_id(self) -> str | None:
        with self._lock:
            return self._active.run_id if self._active and not self._active.done.is_set() else None

    # ------------------------------------------------------------------ internals

    def _execute(self, active: _ActiveRun, options: RunOptions) -> None:
        try:
            active.summary = self._run_pipeline(options)
        except Exception as exc:  # noqa: BLE001 - the thread must always finish and record the outcome
            logger.exception("run %s crashed", active.run_id)
            active.error = f"{type(exc).__name__}: {exc}"[:300]
        finally:
            with self._lock:
                self._finished[active.run_id] = active
            active.done.set()

    def _recent_running_row(self) -> dict | None:
        stale_before = self._clock() - timedelta(minutes=self._settings.stale_running_minutes)
        for row in self._runs.running_runs():
            started = _parse_time(row.get("started_at"))
            if started and started >= stale_before:
                return row
        return None

    def _finished_today(self) -> dict | None:
        latest = self._runs.latest_run()
        if not latest or str(latest.get("status")) not in FINISHED_OK:
            return None
        if not str(latest.get("trigger_id") or "").startswith(SERVICE_TRIGGER_PREFIX):
            return None
        started = _parse_time(latest.get("started_at"))
        return latest if started and started.date() == self._clock().date() else None


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
