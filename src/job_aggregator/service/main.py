"""Service entry point for Render.

  uvicorn job_aggregator.service.main:create_app_from_environment --factory --host 0.0.0.0 --port $PORT

Spike mode: set SPIKE_FAKE_PIPELINE_MINUTES (for example 12) to replace the real pipeline with one that
only sleeps and logs a heartbeat line every minute, to measure cold start and spin-down (tasks.md 16.4).
"""

from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime

from fastapi import FastAPI

from job_aggregator.credentials.secret_redaction import install_secret_redaction, register_secret
from job_aggregator.domain.models import RunStatus, RunSummary
from job_aggregator.orchestration.build_pipeline import DEFAULT_CONFIG_DIR, build_pipeline
from job_aggregator.orchestration.daily_run_pipeline import DailyRunPipeline, RunOptions
from job_aggregator.service.run_manager import RunManager
from job_aggregator.service.web_app import create_app
from job_aggregator.settings.load_env_file import load_env_file
from job_aggregator.settings.read_secrets import read_trigger_secrets

logger = logging.getLogger("job_aggregator.service")


def fake_pipeline_runner(pipeline: DailyRunPipeline, minutes: float):
    """Spike helper: writes a real `runs` row, then sleeps, logging once a minute."""

    def run(options: RunOptions) -> RunSummary:
        runs = pipeline.run_repository
        started = datetime.now(UTC)
        runs.start_run(options.run_id, options.trigger_id, started, {"spike_fake_minutes": minutes})
        for minute in range(int(minutes)):
            logger.info("spike run %s alive: minute %d of %g", options.run_id, minute + 1, minutes)
            time.sleep(60)
        finished = datetime.now(UTC)
        runs.finish_run(options.run_id, RunStatus.SUCCEEDED, finished, f"spike finished after {minutes} min", False)
        logger.info("spike run %s finished", options.run_id)
        return RunSummary(run_id=options.run_id, status=RunStatus.SUCCEEDED, started_at=started,
                          finished_at=finished)

    return run


def create_app_from_environment() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    install_secret_redaction()
    load_env_file()  # no-op on Render (no file); lets the service run locally from .env.local
    secrets = read_trigger_secrets()
    for position, secret in enumerate(secrets, start=1):
        register_secret(secret, f"trigger secret #{position}")

    pipeline = build_pipeline(os.environ.get("JOB_AGGREGATOR_CONFIG_DIR", str(DEFAULT_CONFIG_DIR)))
    spike_minutes = float(os.environ.get("SPIKE_FAKE_PIPELINE_MINUTES", "0") or 0)
    runner = fake_pipeline_runner(pipeline, spike_minutes) if spike_minutes > 0 else pipeline.run

    skip_methods = tuple(m.strip() for m in os.environ.get("SKIP_FETCH_METHODS", "").split(",") if m.strip())
    manager = RunManager(runner, pipeline.run_repository, pipeline.settings.trigger, skip_methods=skip_methods)
    manager.recover_interrupted_runs()
    return create_app(manager, lambda: pipeline.check_health_only(), secrets)
