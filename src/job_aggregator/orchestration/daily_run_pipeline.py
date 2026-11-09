"""The daily run: load, sync registry, fetch, validate, normalise, dedupe, score, persist, health, notify.

Every source is isolated: a failure in one is recorded and the run moves on. With `dry_run` nothing is
written anywhere (no database rows, no seen-post records, no notification); results are printed instead.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from job_aggregator.credentials.secret_redaction import redact_secrets
from job_aggregator.domain.models import (
    NormalizedJob,
    RunStatus,
    RunSummary,
    SearchConfig,
    SourceRunRecord,
    SourceStatus,
    TopMatch,
)
from job_aggregator.fetching.fetch_source_safely import fetch_source_safely
from job_aggregator.fetching.fetcher_factory import FetcherFactory
from job_aggregator.health.evaluate_source_health import detect_missed_run, evaluate_source_health
from job_aggregator.notifications.notifier import Notifier, format_run_summary, ping_heartbeat, send_notification_safely
from job_aggregator.persistence.job_repository import JobRepository
from job_aggregator.persistence.run_repository import RunRepository
from job_aggregator.persistence.search_config_repository import SearchConfigRepository
from job_aggregator.persistence.seen_post_repository import SeenPostRepository
from job_aggregator.persistence.source_repository import SourceRepository
from job_aggregator.processing.normalize_listing import normalize_listing
from job_aggregator.processing.validate_listing import validate_listings
from job_aggregator.registry.source_entry import SourceEntry
from job_aggregator.scoring.build_scorer import score_job_safely
from job_aggregator.scoring.job_scorer import JobScorer
from job_aggregator.settings.app_settings import AppSettings

logger = logging.getLogger(__name__)
LINKEDIN_METHOD = "linkedin_profile_posts"


@dataclass(frozen=True)
class RunOptions:
    trigger_id: str = "manual"
    dry_run: bool = False
    only_sources: tuple[str, ...] = ()
    only_methods: tuple[str, ...] = ()
    skip_methods: tuple[str, ...] = ()
    run_id: str | None = None


@dataclass
class RunContext:
    """Per-run facts handed to the components built for that run."""

    run_id: str
    now: datetime
    dry_run: bool
    record_post_outcome: Callable[[str, str, str, str | None], None]


@dataclass
class RunComponents:
    """Things rebuilt for every run, because they hold per-run state (spent tokens, post budgets)."""

    fetcher_factory: FetcherFactory
    scorer: JobScorer


@dataclass
class Repositories:
    search_config: SearchConfigRepository
    sources: SourceRepository
    runs: RunRepository
    jobs: JobRepository
    seen_posts: SeenPostRepository


@dataclass
class _SourceOutcome:
    record: SourceRunRecord
    new_jobs: list[NormalizedJob] = field(default_factory=list)
    discarded: int = 0
    alert: str | None = None


def select_sources(entries: list[SourceEntry], only_sources: tuple[str, ...] = (),
                   only_methods: tuple[str, ...] = (), skip_methods: tuple[str, ...] = (),
                   enabled_flags: dict[str, bool] | None = None) -> list[SourceEntry]:
    """Enabled entries, narrowed to the given identifiers and/or fetch methods, minus skipped methods.

    `enabled_flags` holds the owner's toggles from the database (the UI wins); an entry without one
    (not yet in the database) uses the registry file's flag.

    `skip_methods` lets one environment (the cloud service) leave out IP-sensitive boards that another
    environment (the owner's PC) fetches, without disabling them in the shared registry file.
    """
    flags = enabled_flags or {}
    selected = [e for e in entries if flags.get(e.id, e.enabled)]
    if only_sources:
        unknown = set(only_sources) - {e.id for e in entries}
        if unknown:
            raise ValueError(f"unknown source id(s): {', '.join(sorted(unknown))}")
        selected = [e for e in selected if e.id in only_sources]
    if only_methods:
        selected = [e for e in selected if e.fetch_method in only_methods]
    if skip_methods:
        selected = [e for e in selected if e.fetch_method not in skip_methods]
    return selected


def overall_status(records: list[SourceRunRecord]) -> RunStatus:
    attempted = [r for r in records if r.status is not SourceStatus.SKIPPED]
    if attempted and all(r.status is SourceStatus.FAILED for r in attempted):
        return RunStatus.FAILED
    if any(r.status in (SourceStatus.FAILED, SourceStatus.BLOCKED, SourceStatus.PARTIAL) for r in records):
        return RunStatus.PARTIAL
    return RunStatus.SUCCEEDED


class DailyRunPipeline:
    def __init__(
        self,
        entries: list[SourceEntry],
        settings: AppSettings,
        repositories: Repositories,
        make_run_components: Callable[[RunContext], RunComponents],
        notifier: Notifier,
        heartbeat_url: str | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        output: Callable[[str], None] = print,
        not_fetched: dict[str, str] | None = None,
    ) -> None:
        self._not_fetched = not_fetched or {}
        self._entries = entries
        self._settings = settings
        self._repos = repositories
        self._make_run_components = make_run_components
        self._notifier = notifier
        self._heartbeat_url = heartbeat_url
        self._clock = clock
        self._output = output

    @property
    def settings(self) -> AppSettings:
        return self._settings

    @property
    def run_repository(self) -> RunRepository:
        return self._repos.runs

    # ------------------------------------------------------------------ daily run

    def run(self, options: RunOptions | None = None) -> RunSummary:
        options = options or RunOptions()
        started = self._clock()
        run_id = options.run_id or str(uuid.uuid4())
        summary = RunSummary(run_id=run_id, status=RunStatus.RUNNING, started_at=started, dry_run=options.dry_run)
        run_row_written = False
        try:
            search_config = self._repos.search_config.load_search_config()
            if not options.dry_run:
                self._repos.sources.sync_registry(self._entries)
            flags = self._repos.sources.enabled_flags([e.id for e in self._entries])
            sources = select_sources(self._entries, options.only_sources, options.only_methods,
                                     options.skip_methods, flags)
            if not options.dry_run:
                self._repos.runs.start_run(run_id, options.trigger_id, started,
                                           self._config_snapshot(sources, search_config, options))
                run_row_written = True

            context = RunContext(run_id, started, options.dry_run,
                                 self._post_outcome_recorder(options.dry_run, started))
            components = self._make_run_components(context)
            health_columns = self._repos.sources.health_columns([s.id for s in sources])
            keys_seen_this_run: set[str] = set()
            alerts: list[str] = []
            new_jobs: list[NormalizedJob] = []

            for source in sources:
                outcome = self._process_source(run_id, source, search_config, components, options.dry_run,
                                               health_columns.get(source.id, {}), keys_seen_this_run)
                summary.source_records.append(outcome.record)
                summary.jobs_found += outcome.record.jobs_found
                summary.jobs_new += outcome.record.jobs_new
                summary.jobs_discarded += outcome.discarded
                new_jobs += outcome.new_jobs
                if outcome.alert:
                    alerts.append(outcome.alert)

            if not options.only_sources and not options.only_methods:
                self._record_unfetched_sources(run_id, summary, options.dry_run)

            if not options.dry_run:
                retired = self._repos.jobs.retire_stale_jobs(
                    self._clock(), search_config.max_job_age_days, self._settings.persistence.stale_after_days_unseen)
                logger.info("retired %d stale job(s)", retired)

            summary.status = overall_status(summary.source_records)
            summary.unhealthy_sources = alerts
            summary.top_matches = self._top_matches(new_jobs)
        except Exception as exc:  # noqa: BLE001 - a run-level failure is recorded, notified, and reported
            logger.exception("run %s failed", run_id)
            summary.status = RunStatus.FAILED
            alerts = [redact_secrets(f"Run failed: {type(exc).__name__}: {exc}")[:300]]
            summary.unhealthy_sources = alerts

        summary.finished_at = self._clock()
        self._finish(summary, alerts, run_row_written)
        return summary

    def _process_source(self, run_id: str, source: SourceEntry, search_config: SearchConfig,
                        components: RunComponents, dry_run: bool, health_row: dict,
                        keys_seen_this_run: set[str]) -> _SourceOutcome:
        started = self._clock()
        try:
            fetcher = components.fetcher_factory.fetcher_for(source)
            result = fetch_source_safely(fetcher, source, search_config,
                                         self._settings.fetching.max_listings_per_source)
            validation = validate_listings(result.listings, search_config.excluded_companies)
            discarded = sum(validation.discard_reasons.values())
            oldest_allowed = (started - timedelta(days=search_config.max_job_age_days)).date()
            jobs: list[NormalizedJob] = []
            for listing in validation.accepted:
                if listing.posted_at and listing.posted_at < oldest_allowed:
                    discarded += 1
                    continue
                try:
                    job = normalize_listing(listing, self._settings.processing, search_config, source.base_url,
                                            source.setting("remote_bucket"))
                except Exception:  # noqa: BLE001 - one bad listing never stops its source
                    logger.exception("could not normalise a listing from %s", source.id)
                    discarded += 1
                    continue
                jobs.append(score_job_safely(components.scorer, job, search_config))

            new_jobs = self._store(jobs, source, dry_run, keys_seen_this_run)
            message = result.message
            if discarded:
                message = f"{message}; {discarded} discarded".strip("; ")
            record = SourceRunRecord(source_id=source.id, status=result.status, jobs_found=len(result.listings),
                                     jobs_new=len(new_jobs), message=redact_secrets(message)[:1000],
                                     block_kind=result.block_kind, started_at=started,
                                     finished_at=self._clock())
        except Exception as exc:  # noqa: BLE001 - isolate the source
            logger.exception("processing %s failed", source.id)
            record = SourceRunRecord(source_id=source.id, status=SourceStatus.FAILED,
                                     message=redact_secrets(f"{type(exc).__name__}: {exc}")[:500],
                                     started_at=started, finished_at=self._clock())
            new_jobs, discarded = [], 0

        alert = self._record_source(run_id, record, dry_run, health_row)
        return _SourceOutcome(record, new_jobs, discarded, alert)

    def _record_unfetched_sources(self, run_id: str, summary: RunSummary, dry_run: bool) -> None:
        """Sources enabled in the UI that this pipeline cannot fetch get an honest 'skipped' row each run.

        Without it the UI would keep showing their last run from the old routine as if they were current.
        """
        registry_ids = {entry.id for entry in self._entries}
        for source_id in sorted(set(self._repos.sources.enabled_source_ids()) - registry_ids):
            reason = self._not_fetched.get(source_id) or "not in the source registry, so the pipeline does not fetch it"
            now = self._clock()
            record = SourceRunRecord(source_id=source_id, status=SourceStatus.SKIPPED, message=reason[:1000],
                                     started_at=now, finished_at=now)
            summary.source_records.append(record)
            if dry_run:
                self._output(f"[dry-run] {source_id:<20} skipped   {reason}")
            else:
                self._repos.runs.record_source_run(run_id, record)

    def _store(self, jobs: list[NormalizedJob], source: SourceEntry, dry_run: bool,
               keys_seen_this_run: set[str]) -> list[NormalizedJob]:
        if not jobs:
            return []
        if dry_run:
            existing = self._repos.jobs.find_existing_keys([j.dedupe_key for j in jobs])
            new = [j for j in dict((j.dedupe_key, j) for j in jobs).values()
                   if j.dedupe_key not in existing and j.dedupe_key not in keys_seen_this_run]
            keys_seen_this_run.update(j.dedupe_key for j in jobs)
            for job in jobs:
                marker = "NEW " if job in new else "seen"
                self._output(f"[dry-run] {source.id:<20} {marker} score={job.fit_score} key={job.dedupe_key}")
            return new
        stored = self._repos.jobs.store_jobs(jobs, self._clock())
        new_keys = set(stored.new_keys)
        new = [j for j in dict((j.dedupe_key, j) for j in jobs).values() if j.dedupe_key in new_keys]
        if source.fetch_method == LINKEDIN_METHOD:
            ids = self._repos.jobs.job_ids_for_keys([j.dedupe_key for j in jobs])
            for job in jobs:
                self._repos.seen_posts.record_post(job.source_url, source.id, "job_created", self._clock(),
                                                   job_id=ids.get(job.dedupe_key))
        return new

    def _record_source(self, run_id: str, record: SourceRunRecord, dry_run: bool, health_row: dict) -> str | None:
        previous = self._repos.runs.recent_source_runs(record.source_id, self._settings.health.baseline_runs)
        health = evaluate_source_health(record.source_id, record.status, record.jobs_found, previous,
                                        int(health_row.get("consecutive_empty_runs") or 0), self._settings.health)
        if dry_run:
            self._output(f"[dry-run] {record.source_id:<20} {record.status.value:<9} found={record.jobs_found} "
                         f"new={record.jobs_new} {record.message}")
            return health.alert
        self._repos.runs.record_source_run(run_id, record)
        succeeded = record.status in (SourceStatus.SUCCEEDED, SourceStatus.PARTIAL) and record.jobs_found > 0
        self._repos.sources.update_health(record.source_id, health.empty_run_streak,
                                          record.finished_at if succeeded else None)
        return health.alert

    # ------------------------------------------------------------------ health-only mode

    def check_health_only(self, dry_run: bool = False) -> list[str]:
        """Missed-run check plus sources stuck at zero; sends one alert when anything is wrong."""
        now = self._clock()
        latest = self._repos.runs.latest_run()
        latest_started = datetime.fromisoformat(latest["started_at"]) if latest and latest.get("started_at") else None
        alerts = []
        if missed := detect_missed_run(latest_started, now, self._settings.health.missed_run_hours):
            alerts.append(missed)
        threshold = self._settings.health.consecutive_empty_runs_alert
        flags = self._repos.sources.enabled_flags([e.id for e in self._entries])
        watched = select_sources(self._entries, enabled_flags=flags)
        columns = self._repos.sources.health_columns([e.id for e in watched])
        for source_id, row in columns.items():
            if int(row.get("consecutive_empty_runs") or 0) >= threshold:
                alerts.append(f"{source_id} returned no jobs for {row['consecutive_empty_runs']} runs in a row")
        if alerts and not dry_run:
            send_notification_safely(self._notifier, "Job pipeline health alert", "\n".join(alerts), "high")
        for alert in alerts:
            self._output(f"[health] {alert}")
        if not alerts:
            self._output("[health] all checks passed")
        return alerts

    # ------------------------------------------------------------------ helpers

    def _finish(self, summary: RunSummary, alerts: list[str], run_row_written: bool) -> None:
        title, body, priority = format_run_summary(summary, alerts)
        if summary.dry_run:
            self._output(f"[dry-run] {title}\n{body}")
            return
        summary.notification_error = send_notification_safely(self._notifier, title, body, priority)
        if run_row_written:
            text = json.dumps({
                "jobs_found": summary.jobs_found, "jobs_new": summary.jobs_new,
                "jobs_discarded": summary.jobs_discarded, "alerts": alerts,
                "notification_error": summary.notification_error,
            })
            try:
                self._repos.runs.finish_run(summary.run_id, summary.status, summary.finished_at, text,
                                            notified=summary.notification_error is None)
            except Exception:  # noqa: BLE001
                logger.exception("could not record the end of run %s", summary.run_id)
        if summary.status is RunStatus.SUCCEEDED:
            ping_heartbeat(self._heartbeat_url, self._settings.notifications.heartbeat_enabled)

    def _top_matches(self, new_jobs: list[NormalizedJob]) -> list[TopMatch]:
        settings = self._settings.notifications
        good = [j for j in new_jobs if (j.fit_score or 0) >= settings.min_score_for_top_match]
        good.sort(key=lambda j: (-(j.fit_score or 0), -(j.posted_at or date.min).toordinal()))
        return [TopMatch(title=j.title, company=j.company, fit_score=j.fit_score or 0, apply_url=j.apply_url)
                for j in good[: settings.top_matches_count]]

    def _post_outcome_recorder(self, dry_run: bool, now: datetime) -> Callable[[str, str, str, str | None], None]:
        def record(post_url: str, source_id: str, outcome: str, note: str | None) -> None:
            if not dry_run:
                self._repos.seen_posts.record_post(post_url, source_id, outcome, now, note=note)  # type: ignore[arg-type]
        return record

    def _config_snapshot(self, sources: list[SourceEntry], search_config: SearchConfig,
                         options: RunOptions) -> dict:
        return {
            "sources": [s.id for s in sources],
            "only_sources": list(options.only_sources),
            "only_methods": list(options.only_methods),
            "skip_methods": list(options.skip_methods),
            "search_config": search_config.model_dump(),
            "gemini_enabled": self._settings.scoring.gemini.enabled,
        }
