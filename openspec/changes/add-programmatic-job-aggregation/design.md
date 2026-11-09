# Design

## Context

See proposal.md for motivation. The repository is empty apart from OpenSpec scaffolding, so this is a greenfield Python project that must plug into an existing Supabase database already used by a read-only UI.

Observed constraints from the live database and the current Claude routine:

- Tables in use: `sources`, `search_config` (single row, `id = 1`), `runs`, `source_runs`, `source_run_queries`, `jobs`, `job_sources`; the UI reads a `job_feed` view over `jobs` and `applications`.
- `runs.run_id` has no default, which broke the routine's first insert; the pipeline must supply its own UUID.
- `sources` already carries `id`, `name`, `base_url`, `access_method`, `enabled`, `consecutive_empty_runs`, `last_success_at`, plus template columns the routine used. `access_method` may be constrained to a fixed set of values; this is unverified.
- Existing dedupe keys look like `company|title|location` in lowercase with punctuation removed (for example `jpmorganchase|software engineer ii java springboot react rdbms kubernetes|mumbai`).
- `source_runs.status` accepts `partial` and `skipped`; `needs_login` and `error` also appear historically.
- Only seven sources produced new jobs in the last 30 days (Indeed, Jobcode, Wellfound, Foundit, Himalayas, one LinkedIn profile, Instahyre); the rest never returned data.
- Supabase free projects pause after a week without database activity; a daily write prevents that.

## Goals / Non-Goals

**Goals:**
- Every enabled source is attempted on every run, and each outcome is recorded.
- Adding or disabling a source or LinkedIn profile is an edit to one text file.
- Every module has one reason to change, and names state what a module or function does.
- The pipeline runs as a hosted service started by an external daily trigger and, for a subset of sources, from the owner's machine against the same database.
- Zero running cost under normal volume.

**Non-Goals:**
- Changing the UI, the `jobs` schema columns, or the `job_feed` view.
- Logging in to any site, solving challenges, or parsing alert emails.
- Replacing the database with another store.
- A general-purpose scraping framework; only the source types in the specs are built.

## Decisions

### D1. Layered package with ports and adapters
The code is split so business rules never import a vendor library directly:

```
config/
  sources.yaml            registry: websites + LinkedIn profiles (source of truth)
  settings.yaml           non-secret behaviour: limits, retries, thresholds, channel
src/job_aggregator/
  domain/                 plain data models and error types (no I/O)
  registry/               load_source_registry, validate_source_registry
  settings/               load_settings, read_secret_lists_from_environment
  credentials/            CredentialPool, rotate_on_quota_error, per-service error classifiers
  fetching/
    job_fetcher.py        JobFetcher interface
    fetcher_factory.py    maps fetch_method -> fetcher
    open_api/             jobcode, himalayas, remotive, remoteok fetchers
    ats_boards/           greenhouse, lever, ashby fetchers
    job_boards/           jobspy_board_fetcher
  linkedin/               fetch_profile_posts, parse_hiring_post, resolve_short_link
  processing/             normalize_listing, build_dedupe_key, validate_listing
  scoring/                RulesScorer, GeminiScorer, build_scorer
  persistence/            job_repository, run_repository, seen_post_repository, supabase_client
  health/                 evaluate_source_health, detect_missed_run
  notifications/          Notifier interface, ntfy_notifier
  orchestration/          daily_run_pipeline, run_daily (CLI entry point), build_pipeline (composition root)
  service/                web app: trigger endpoints, shared-secret auth, run manager (background run, overlap guard)
tests/                    unit tests plus saved sample payloads
migrations/               reviewable SQL files, applied only on approval
render.yaml               Render web service definition (no secret values)
.github/workflows/        daily trigger, health-check trigger, and manual-only fallback workflow
```

Dependencies point inward: orchestration knows interfaces, adapters implement them, and `build_pipeline` is the only place that wires concrete classes together. This is what makes fetchers, scorers and notifiers replaceable without touching the pipeline.
*Alternatives:* one script per source (fast to write, duplicates retry, logging and persistence code, and gives no shared status model); a plugin framework (more machinery than seven sources justify).

### D2. Two configuration files, secrets only in the environment
`config/sources.yaml` lists every target; `config/settings.yaml` holds tunables. Secrets are never in either file.

Registry entry shape (illustrative, not final field names):
```
- id: himalayas
  name: Himalayas
  fetch_method: open_api
  provider: himalayas
  enabled: true
- id: li_swadesh_kumar
  name: Swadesh Kumar (LinkedIn)
  fetch_method: linkedin_profile_posts
  profile_url: https://www.linkedin.com/in/swadesh-kumar/
  posts_per_run: 3
  enabled: true
```
Validation fails the whole run before any fetch when an entry is malformed, duplicated or names an unknown method.
*Alternative considered:* keep the `sources` table as the only registry. Rejected because the user wants a file a developer can read and review in version control.

### D3. The file is the source of truth and is synchronised into the `sources` table
At the start of a run the registry is upserted into `sources` so run history keeps its foreign keys and the UI still sees names and enabled flags. The sync writes only `id`, `name`, `base_url` and `enabled` for existing rows. For new rows, `access_method` is set from a small mapping to the nearest existing value. Before any sync is built, the allowed `access_method` values must be read from the database so the sync cannot violate a constraint. The existing `consecutive_empty_runs` and `last_success_at` columns are reused for health tracking instead of adding new ones.
*Alternative:* write every registry field to the table. Rejected because it risks check-constraint failures and duplicates settings that belong in the file.

### D4. Fetchers share one interface and are chosen by a factory
Every fetcher implements `fetch(source, search_config) -> FetchResult` and returns the common raw listing shape plus a status and message. `fetcher_factory` maps the registry's `fetch_method` (`open_api`, `ats_board`, `jobspy_board`, `linkedin_profile_posts`) to a class through a lookup table, so adding a method means adding a class and one table entry.
Retries, pacing, timeouts and the "failure of one source never stops the others" rule live in one wrapper around every fetcher rather than inside each one.
*Alternative:* branching on method inside the pipeline. Rejected because it grows with every source and mixes control flow with site details.

### D5. Credential pool with per-service error classification
`CredentialPool` holds an ordered list of tokens per service, read from one environment value per service containing a separated list (for example `APIFY_TOKENS`, `GEMINI_API_KEYS`). `rotate_on_quota_error` runs a call, asks a per-service classifier whether the failure means quota, rate limit or a rejected token, marks that token unavailable for the run, and retries with the next. Other failures are not retried with a new token. Logs identify tokens by position only.
Apify's exact quota and invalid-token responses are not confirmed; the classifier table is filled from a real exhausted-token response during the Apify spike rather than guessed.
*Alternative:* one token per secret name read in a loop. Rejected because a single list per service is easier to extend in the hosting environment's secrets and keeps the pool logic in one place.

### D6. LinkedIn posts via Apify, parsed by a template-aware parser
`fetch_profile_posts` calls the harvestapi LinkedIn profile posts actor with the pool, requesting only the newest N posts per profile. `parse_hiring_post` accepts a post only if it has a configured hiring marker (for example "IS HIRING") and an apply link, then reads labelled lines through an alias map (Role or Position, Experience, Batch, Location, Skills, Stipend or CTC, Apply link). Marker phrases and aliases live in `settings.yaml`, so a new influencer's wording is a config change. `resolve_short_link` fetches the `lnkd.in` page with plain HTTP and takes the single non-LinkedIn link in it; this was verified by hand for two links. Posts are recorded by URL in a seen-posts table with an outcome (`job_created`, `ignored`, `unparsed`).
*Alternatives:* an LLM to extract fields (costs tokens for text that is already labelled); the Apify post scraper from other vendors (less used, no cost advantage).

### D7. Persistence through repositories with idempotent writes
`job_repository` upserts on the dedupe key, updates `last_seen_at` for jobs already stored, and writes one `job_sources` link per source. `build_dedupe_key` reproduces the existing format and is checked against a sample of live keys before use. Re-running a failed run cannot create duplicates because writes are keyed. The database client is Supabase's REST interface with the service key, chosen over a direct Postgres connection because it needs no network exceptions in the scheduler and no connection string. This depends on a unique constraint on `jobs.dedupe_key`; if it is absent it is added through an approved migration.
*Alternative:* direct Postgres with `INSERT ... ON CONFLICT`. Kept as the fallback if the REST interface cannot express a needed write.

### D8. Rules first, optional Gemini behind a flag
`RulesScorer` computes a 1–5 score from `search_config` (keyword and skill overlap, location, years of experience against `max_required_yoe`, salary against `min_salary_lpa`, `excluded_companies`) and flags internships and batch-restricted roles. Weights and keyword lists are in `settings.yaml`. `GeminiScorer` is off by default; when enabled it reviews only borderline jobs, sends minimal text, uses the credential pool, and falls back to the rules on any failure. `build_scorer` picks the implementation from settings.
*Alternative:* a model for every job. Rejected: it costs quota, adds privacy exposure for the owner's profile, and the posts and API results are already structured.

### D9. Orchestration, health and notification
`daily_run_pipeline` runs load, sync, fetch, validate, normalise, dedupe, score, persist, health, notify in that order and records one `runs` row (its UUID generated client-side) and one `source_runs` row per source. Command-line options allow `--only-sources`, `--only-methods` and `--dry-run`, which is how the owner's machine runs only the job-board sources. Health checks compare each source's count with its recent average from `source_runs` and flag zero or sharply low results over a configurable number of runs. A separate `--check-health-only` mode, exposed as a health-check endpoint and called by a second workflow at a different hour, detects a missed run. An optional heartbeat URL can be pinged on success so an external service can alert if pings stop, because a dead scheduler also kills the watchdog. `Notifier` is an interface; the default implementation is ntfy.sh with a secret topic, an assumption the owner can swap for another channel through settings.

### D10. Hosting: Render web service woken by a GitHub Actions cron
The owner chose a Render service started by a GitHub cron. The shape:

```
GitHub Actions (daily cron, private repo)          Render web service (free)
  POST /runs  (Bearer secret) ----retry/backoff--> accepts, returns 202 + run_id
  GET  /runs/{id} every ~60s  ------------------>  status; this traffic also keeps
  ... until finished or limit                       the instance awake during the run
                                                    background run: daily_run_pipeline
  second cron, other hour:
  POST /health-check ---------------------------->  check_health_only (missed run, sources)
```

- **Endpoints** (in `service/`): start a run (returns 202 with a run id), run status, health check, and an unauthenticated liveness endpoint that returns no data.
- **Background run:** a run manager starts `daily_run_pipeline` in a background thread so the run never depends on the request staying open. It allows one active run: an in-process lock plus a check of `runs` for a row still marked running. A second start returns the active run's id. Whether a repeat trigger after a finished day starts a new run or returns the finished run is a setting. Because state lives in the `runs` table, a restarted instance reports a run left marked running as interrupted.
- **Authentication:** `Authorization: Bearer <secret>` checked in constant time against a list (`TRIGGER_SECRETS`, separated values) so a new secret is added before the old one is removed. Secrets are never logged.
- **Secrets split:** the Supabase key, Apify and Gemini token lists, ntfy topic and `TRIGGER_SECRETS` are Render environment variables. GitHub holds only the trigger URL and one trigger secret.
- **Cold start:** the trigger workflow retries start with backoff for a configurable wait, then polls status until the run finishes or a limit passes. Failure at either point fails the workflow, which gives the owner GitHub's failure email at no cost.
- **No Render scheduler:** Render's own cron jobs are not free and are not used.
- **Local run:** the owner's PC with Windows Task Scheduler runs the job-board subset through the CLI, because it has a residential IP.
- **Fallback:** if the spike (tasks group 16) shows a free instance cannot finish the run, a manual-dispatch GitHub workflow runs the CLI inside the Actions job (private repo, about 2,000 Linux minutes a month against roughly 300 used). That workflow is written either way so the switch is a change of which workflow has the schedule.

Unverified and settled by the spike: whether the background thread survives with no incoming requests, whether polling traffic really prevents spin-down, how long a cold start takes, and the free plan's hours and bandwidth limits, which were reported by third parties and not read from Render's documentation.
*Alternatives:* running the pipeline inside the GitHub Actions job (simpler, no cold start, kept as the fallback); Cloudflare Workers (free CPU time per run is too small); Oracle's free VM (capacity and signup friction); Supabase scheduled functions (poor fit for long fetch loops).

### D11. Database changes through reviewable migrations only
`migrations/` holds SQL files: a default for `runs.run_id`, a seen-posts table with row-level security enabled and no public policies, and a unique index on `jobs.dedupe_key` if one is missing. Nothing is applied to the live database without the owner's approval, and each file is written to be safe to run twice.

### D12. Testing without live network
Unit tests cover the registry validator, credential rotation, post parser (using the two example posts as fixtures), link resolver (against saved pages), dedupe key, rules scorer and health evaluation. Each fetcher has a contract test against a saved sample payload. Service tests use the framework's test client with a fake pipeline: authentication (missing, wrong, either of two secrets), the 202 response, overlap refusal, status after finish and after restart, and that no secret appears in output. Live checks are limited to the manual spikes, run with `--dry-run` where they touch the database.

## Risks / Trade-offs

- [JobSpy sources blocked from Render's IP ranges] → run the job-board subset from the owner's machine; Apify Naukri and Foundit actors remain a paid fallback outside the free credit.
- [Free Render instance spins down or is throttled mid-run, or a background thread is not kept alive without requests] → status polling keeps traffic flowing, the run is recorded in `runs` so an interrupted run is visible, a spike measures it, and the fallback runs the pipeline inside the GitHub Actions job.
- [Cold start makes the first trigger fail] → retry with backoff for a configured wait, then fail visibly.
- [Free hours or bandwidth limits unverified] → read them from Render's dashboard before relying on the plan; a daily run plus polling is small.
- [Public endpoint attacked or abused] → every data endpoint needs a rotatable secret, only one run can be active, and the liveness endpoint returns nothing.
- [Scrapers break silently when a site changes] → health baselines and per-source status make a drop visible in the notification.
- [Apify actor changes, disappears or raises prices] → the fetcher sits behind the interface, so another actor or provider replaces it without touching other code; per-run post cap keeps cost bounded.
- [LinkedIn changes the `lnkd.in` page] → resolver failure keeps the short link and flags the job unresolved rather than losing it.
- [Terms and attribution for open APIs] → keep source name and original URL on each job; data stays private; respect Remotive's roughly four calls a day by caching or skipping extra calls in the same day.
- [GitHub schedule drift or skipped runs] → off-peak minute, manual dispatch, missed-run watchdog and optional heartbeat.
- [Service key held in Render environment variables can read and write everything] → used only by the pipeline, never exposed to the UI, logs or GitHub; rotate if leaked.
- [Free-tier quotas change] → limits live in settings, tokens rotate, and the optional model scorer is off by default.
- [Registry and `sources` table diverge] → the file always wins and is synchronised at the start of every run.

## Migration Plan

1. Build and test locally; run with `--dry-run` against the real database for read-only checks.
2. Deploy the service to Render and run the Render spike first; if it fails, switch to the fallback workflow before building further on the service.
3. Run the other spikes (JobSpy from Render's IP ranges; Apify post output) and adjust settings.
4. With approval, apply migrations, then enable the daily trigger workflow alongside the Claude routine and compare coverage for several days.
5. After the owner approves parity, disable the Claude routine.
6. Rollback: disable the trigger workflows and re-enable the Claude routine; stored jobs and run history stay valid because the schema is unchanged except for additive items.

## Open Questions

- Does the owner prefer a different notification channel than ntfy.sh? It is a setting, so this does not change the structure.
- Which company slugs should the ATS board fetchers watch? This is registry content, supplied later.
- Which heartbeat service, if any, should receive the success ping?
- What are the free Render plan's monthly hours and bandwidth limits? Read them from Render's dashboard or documentation; they were reported by third parties only.
- Should a repeat trigger after a finished day start another run or return the finished one? Default proposed: return the finished run; it is a setting.
