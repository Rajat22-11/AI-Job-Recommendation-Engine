# Architecture

## Layers

```
config/sources.yaml, config/settings.yaml, environment secrets
        |
        v
orchestration/build_pipeline.py      composition root: the only place concrete classes are wired together
        |
        v
orchestration/daily_run_pipeline.py  run order, per-source isolation, dry run, health-only mode
   |          |            |             |            |             |            |
   v          v            v             v            v             v            v
fetching/  linkedin/  processing/    scoring/   persistence/    health/   notifications/
(fetchers  (Apify,    (validate,     (rules,    (repositories  (source    (ntfy, run
 behind a   parse,     normalise,     optional   behind a       health,    summary,
 factory)   resolve)   dedupe key)    Gemini)    DB port)       missed run) heartbeat)
   |          |
   v          v
credentials/ (token pools, rotation, redaction)        domain/ (plain models and errors, no I/O)

service/  web endpoints + run manager, wrapping the same pipeline for Render
```

Dependencies point inward:
- The pipeline knows only interfaces: `JobFetcher`, `JobScorer`, `Notifier`, the `DatabaseClient` port.
- Adapters implement them: each fetcher, `RulesScorer` and `GeminiScorer`, `NtfyNotifier`, `SupabaseDatabaseClient`.
- `build_pipeline` chooses the adapters, so you can replace a fetcher, scorer or channel without touching the pipeline.

Per-run state is rebuilt for every run by `make_run_components`: the token pools (tokens spent today), the LinkedIn post budget, the Gemini review budget and the HTTP pacing. A long-lived service never carries one run's exhausted tokens into the next.

## Run order (`DailyRunPipeline.run`)

1. Select enabled registry entries, narrowed by `--only-sources`, `--only-methods` and `--skip-methods`.
2. Read `search_config` (id = 1).
3. Sync the registry into `sources`: create missing rows and keep `access_method` current. The UI's `enabled`, name, base URL and notes are never overwritten, and `enabled` is read back from the database, so a UI toggle wins.
4. Insert the `runs` row with a client-generated UUID, status `running`.
5. For each source, isolated from the others:
   1. **Fetch:** retries, pacing and block detection; a block is recorded and never bypassed.
   2. **Validate:** discard listings with no title, company or apply URL, or from an excluded company.
   3. **Discard old listings:** drop anything older than `max_job_age_days`.
   4. **Normalise** into `jobs` fields and build the `company|title|location` dedupe key.
   5. **Score:** rules, plus the optional model for borderline jobs; a scoring error gives a neutral score.
   6. **Store:** insert new keys, refresh `last_seen_at` for known ones, link each source in `job_sources`. LinkedIn posts that became jobs are recorded in `linkedin_seen_posts`.
   7. **Record:** write the `source_runs` row and update `sources.consecutive_empty_runs` and `last_success_at`. Collect health alerts.
6. Record a `skipped` row, with its reason from `not_fetched`, for every source enabled in the UI that the pipeline does not fetch (full runs only, not `--only-*` runs).
7. Retire stale jobs (mark inactive; never delete).
8. Send one notification: counts, top matches, problem sources and health alerts. If the channel is down, the run still finishes and the failure is recorded.
9. Finish the `runs` row: `succeeded`, `partial` or `failed`, with a JSON summary. Ping the heartbeat on success.

With `--dry-run`, steps 3, 4, 5.6 (writes), 5.7 (writes), 6, 7 and 8 write nothing. The run only reads the database and prints each job's key, score and new/seen status.

`--check-health-only` skips the run. It alerts when no run was recorded within `health.missed_run_hours`, or when a source's `consecutive_empty_runs` is at the threshold.

## Command line

```
job-aggregator [--dry-run] [--only-sources ID,...] [--only-methods METHOD,...] [--skip-methods METHOD,...]
               [--check-health-only] [--trigger-id TEXT] [--config-dir DIR] [--verbose]
```

| Example | Effect |
|---|---|
| `job-aggregator --dry-run` | Full run that writes nothing; prints keys and scores |
| `job-aggregator --only-sources indeed,naukri` | Only those registry entries |
| `job-aggregator --only-methods jobspy_board --trigger-id pc-task-scheduler` | The PC's job-board run |
| `job-aggregator --skip-methods jobspy_board` | Everything except the job boards |
| `job-aggregator --check-health-only` | Missed-run and stuck-source alerts only |
| `python -m job_aggregator.registry.check_source_registry` | Validate `config/sources.yaml` and list entries |

Exit codes: `0` succeeded, `1` partial, `2` failed. In health-only mode, `2` means alerts were raised.

## Service endpoints (Render)

Started with `uvicorn job_aggregator.service.main:create_app_from_environment --factory`.

| Endpoint | Auth | Answer |
|---|---|---|
| `GET /healthz` | none | `204`, empty body (liveness only) |
| `POST /runs` body `{"trigger_id": "...", "force": false, "only_sources": [], "only_methods": []}` | Bearer secret | `202 {"run_id", "started", "state", "reason"}` |
| `GET /runs/{run_id}` | Bearer secret | `{"run_id", "state", "started_at", "finished_at", "summary"}`; state is `running`, `succeeded`, `partial`, `failed` or `interrupted` |
| `POST /health-check` | Bearer secret | `{"alerts": [...]}` |

`Authorization: Bearer <secret>` must match one of `TRIGGER_SECRETS`. The comparison is constant-time, and secrets are never logged or echoed. `RunManager` allows one active run:
- A second start returns the active run's id.
- A start after today's run has finished returns that run, unless `force` is set or `repeat_trigger_behaviour` is `start_new`.
- Service runs left `running` by a dead process are marked `interrupted` at start-up and on status checks.

## Where to change things

| To… | Change |
|---|---|
| Add or disable a website or LinkedIn profile | `config/sources.yaml` |
| Tune limits, retries, scoring weights, alerts | `config/settings.yaml` |
| Change keywords, locations, salary, experience, excluded companies | `search_config` table |
| Add a new kind of source | a `JobFetcher` class + `FETCH_METHOD_REQUIRED_SETTINGS` + one line in `build_pipeline.make_run_components_factory` |
| Add a notification channel | a `Notifier` class + `notifications.channel` value + `build_pipeline.build_notifier` |
| Change the database schema | a reviewed file in `migrations/`, applied by hand after approval |
