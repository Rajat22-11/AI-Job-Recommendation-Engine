"""Command-line entry point: `job-aggregator [options]` or `python -m job_aggregator.orchestration.run_daily`.

Exit codes: 0 succeeded, 1 partial, 2 failed (or health alerts in --check-health-only mode).
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable

from job_aggregator.credentials.secret_redaction import install_secret_redaction
from job_aggregator.domain.models import RunStatus
from job_aggregator.orchestration.build_pipeline import DEFAULT_CONFIG_DIR, build_pipeline
from job_aggregator.orchestration.daily_run_pipeline import DailyRunPipeline, RunOptions
from job_aggregator.settings.load_env_file import load_env_file

EXIT_CODES = {RunStatus.SUCCEEDED: 0, RunStatus.PARTIAL: 1, RunStatus.FAILED: 2}


def _csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="job-aggregator", description="Run the daily job aggregation pipeline.")
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch, parse and score, print the results, and write nothing anywhere")
    parser.add_argument("--only-sources", type=_csv, default=(), metavar="ID[,ID...]",
                        help="run only these registry identifiers, e.g. indeed,naukri")
    parser.add_argument("--only-methods", type=_csv, default=(), metavar="METHOD[,METHOD...]",
                        help="run only these fetch methods, e.g. jobspy_board")
    parser.add_argument("--skip-methods", type=_csv, default=(), metavar="METHOD[,METHOD...]",
                        help="leave out these fetch methods, e.g. jobspy_board when the PC fetches them")
    parser.add_argument("--check-health-only", action="store_true",
                        help="only check for a missed run and sources stuck at zero, then alert")
    parser.add_argument("--trigger-id", default="cli", help="recorded in runs.trigger_id (default: cli)")
    parser.add_argument("--config-dir", default=str(DEFAULT_CONFIG_DIR),
                        help="folder with sources.yaml and settings.yaml")
    parser.add_argument("--verbose", action="store_true", help="debug logging")
    return parser.parse_args(argv)


def use_utf8_output() -> None:
    """Job titles contain characters a Windows console code page cannot print; never fail on output."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def configure_logging(verbose: bool) -> None:
    use_utf8_output()
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    install_secret_redaction()


def main(argv: list[str] | None = None,
         pipeline_builder: Callable[[argparse.Namespace], DailyRunPipeline] | None = None) -> int:
    args = parse_arguments(argv)
    configure_logging(args.verbose)
    load_env_file()
    builder = pipeline_builder or (lambda parsed: build_pipeline(parsed.config_dir))
    pipeline = builder(args)
    if args.check_health_only:
        alerts = pipeline.check_health_only(dry_run=args.dry_run)
        return 2 if alerts else 0
    summary = pipeline.run(RunOptions(trigger_id=args.trigger_id, dry_run=args.dry_run,
                                      only_sources=args.only_sources, only_methods=args.only_methods,
                                      skip_methods=args.skip_methods))
    print(f"run {summary.run_id}: {summary.status.value}; found {summary.jobs_found}, new {summary.jobs_new}")
    return EXIT_CODES.get(summary.status, 2)


if __name__ == "__main__":
    sys.exit(main())
