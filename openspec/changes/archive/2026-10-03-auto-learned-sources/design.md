## Context

Verified against the live database (project `ooqayggwtfhrqhsovbhd`, Postgres 17) on 2026-10-03:

- Every public table has RLS enabled and **no policies**. The app reads and writes only with the service role (`src/lib/db/client.ts`, `server-only`), which bypasses RLS. Anon and authenticated roles get nothing.
- `job_feed` is a view with `security_invoker = true` and an **explicit column list**, so new `jobs` columns don't appear in it automatically.
- `sources.access_method` is `NOT NULL` with CHECK (`connector`, `public_scrape`, `browser_session`). `source_runs.status` has CHECK (`ok`, `needs_login`, `captcha`, `error`, `skipped`). Neither `source_runs.run_id` nor anything else references a runs table.
- Migration history holds one entry, `20261002190056_init_job_aggregator_schema`, whose SQL is stored in `supabase_migrations.schema_migrations.statements`. The repo has no `supabase/` folder.
- Data: 5 sources (4 with templates; `indeed` is a connector without one), 21 `source_runs` across 5 run ids, 3 of them `ok` with a `PARTIAL:` message.
- Code that fights a learning trigger today: `updateSourceFields` writes every field, including `access_method` (validated by `z.enum(ACCESS_METHODS)`) and `search_url_template` (validated by `templateError`, which rejects unknown placeholders).

The trigger detects which of these features exist and falls back when they don't, so the migration and the UI can ship independently, migration first.

## Goals / Non-Goals

**Goals:**
- One migration that is additive, idempotent, and safe to apply during a run.
- The app never overwrites trigger-owned state (`search_url_template` learned values, `template_*`, `consecutive_empty_runs`, `last_success_at`, `scrape_hints`) except through the explicit override and Re-learn actions.
- The repo's migration files match the database's migration history.

**Non-Goals:**
- Any scraping, template discovery or verification logic in the app.
- Feed, job detail and run-history UI (follow-up changes `feed-visibility-cues` and `run-history`), although their columns and tables are created here so there is one migration.
- Editing `scrape_hints` from the UI (read-only for now).
- Deleting sources.

## Decisions

### 1. Migrations live in this repo, applied through the Supabase migration API

`supabase/migrations/20261002190056_init_job_aggregator_schema.sql` is written from the stored statements of the existing migration (a baseline, never re-run). The new migration is applied with the Supabase MCP `apply_migration` (name `auto_learned_sources`). That tool assigns the version, so the file is named after the version it records, and the task list checks that `list_migrations` and the folder agree.

*Alternative*: the Supabase CLI with `supabase db push`. Rejected for now because it needs a linked project and a database password on the developer's machine, and adds a tool the project doesn't otherwise use. The files stay CLI-compatible, so switching later is possible.

### 2. Migration shape

All in one transaction with `SET LOCAL lock_timeout = '5s'` and `SET LOCAL statement_timeout = '60s'`. If the trigger holds a conflicting lock, the migration fails fast and is retried rather than queueing behind the trigger and blocking its next writes.

| Object | Statement pattern | Why it's safe |
|---|---|---|
| New columns | `ALTER TABLE … ADD COLUMN IF NOT EXISTS … DEFAULT <constant>` | Constant defaults are metadata-only on PG 11+, with no table rewrite |
| CHECK constraints | `DROP CONSTRAINT IF EXISTS x; ADD CONSTRAINT x CHECK (…) NOT VALID; VALIDATE CONSTRAINT x;` | Re-runnable; every new set is a superset of the old one, so existing rows and trigger writes stay valid |
| `access_method` | `DROP NOT NULL`, `SET DEFAULT 'auto'`, CHECK allows NULL | Matches the trigger contract ("allow NULL/'auto'"). The app always writes `auto` |
| Backfill templates | `UPDATE sources SET template_origin='manual', template_status='verified' WHERE search_url_template IS NOT NULL AND template_origin IS NULL` | The guard makes it run once; a second run touches no rows |
| Backfill links | `UPDATE jobs SET apply_url_kind='board' WHERE apply_url_kind IS NULL` | Same |
| `runs`, `source_run_queries` | `CREATE TABLE IF NOT EXISTS`, `ENABLE ROW LEVEL SECURITY`, `CREATE INDEX IF NOT EXISTS source_run_queries_source_run_idx (source_id, run_id)` | No policies, matching every existing table |
| `job_feed` | `CREATE OR REPLACE VIEW job_feed WITH (security_invoker = true) AS …` with `apply_url_kind` added as the **last** column | Postgres only allows appending columns on replace. The option is restated so it can't be dropped |

Named constraints: `sources_access_method_check` (replaced), `source_runs_status_check` (replaced), `sources_template_status_check`, `sources_template_origin_check`, `source_run_queries_status_check`, `jobs_apply_url_kind_check`.

`source_run_queries.run_id` gets **no foreign key** to `runs`. `source_runs.run_id` has none either, and the trigger may write query rows on a path where it hasn't written (or can't write) a `runs` row. `source_run_queries.source_id` references `sources(id)` as the contract says. `runs.notified` defaults to `false`. `source_runs.config_snapshot jsonb` is added as nullable.

### 3. Template state is derived in one pure function

`templateState(source)` returns `not_applicable | waiting | waiting_to_verify | verified | failed`, plus a `disabled` flag. The access-method rule comes first (`connector`, `api`, `rss` → not applicable), so the backfill doesn't need to special-case `indeed`. This keeps answer B ("not applicable") a display rule, with no data change the trigger would need to know about. The function is unit-tested and used by both `/sources` and the settings summary.

### 4. Effective run status

`effectiveRunStatus(status, message)` maps `ok` with a message matching `/^partial:/i` to `partial`. Everything else passes through. Labels and tones are keyed on the effective status. `needsLogin` keeps reading the raw status, so the banner logic is unchanged.

### 5. Edit form writes only what changed

The plain edit form submits name, base URL, requires login, enabled and notes. The update payload contains exactly those keys.

The Advanced override is a `<details>` block (works without JavaScript) with `access_method` and `search_url_template` inputs, plus hidden `orig_access_method` and `orig_search_url_template` holding the loaded values. On save:
- a field equal to its original is left out of the update;
- a changed template goes through `templateError` and then writes `template_origin`, `template_status` and `template_verified_at` as the spec says.

The remaining race is the user changing the override while the trigger changes the same field. That is rare, and the user's explicit choice wins, which is correct for an override.

*Alternative*: optimistic concurrency with `.eq('search_url_template', orig)`. Rejected: it adds a confusing "changed under you" error for a single-user app.

### 6. Id derivation

`deriveSourceId(name, baseUrl, taken)` is a pure function that is unit-tested. Collisions are checked against ids loaded in the same action, and the unique-violation error (`23505`) on insert is still handled: the action retries once with the next suffix, and if that also fails it shows a form error. The same-host check compares `URL.host` without `www.`, case-insensitively.

### 7. Query coverage query

For each source, take the `run_id` of its latest `source_runs` row, then select `source_run_queries` by `(source_id, run_id)`, which uses the new index. With about 5 sources this is about 5 small queries per page load, run in parallel like the existing `recentRuns`. Counting and grouping happen in a pure, tested function.

## Risks / Trade-offs

- [Schema now owned by two parties (app migrations, trigger behaviour)] → The trigger only writes data and never DDL. The migration header comment and the README state that DDL changes go through `supabase/migrations/` in this repo.
- [Recreating `job_feed` without `security_invoker` would expose jobs and applications to the anon key] → The option is stated explicitly in the migration, and a task checks `pg_class.reloptions` afterwards and runs an anon-key select that must return nothing.
- [Lock wait during a run] → `lock_timeout` makes the migration fail fast. Retry after the run, or right away since runs are daily.
- [Old UI deployed between migration and app deploy] → The old edit form rejects a source the trigger switched to `api`/`rss`/`auto`, which is a validation error and not data loss. Deploy the app right after the migration.
- [`consecutive_empty_runs` threshold of 3 is an app-side guess] → It's a single constant in `src/lib/sources.ts` and easy to tune.
- [MCP-assigned migration version differs from a hand-picked file name] → Name the file after the version that `list_migrations` reports after applying.

## Migration Plan

1. Commit the baseline migration file (no database action).
2. Apply `auto_learned_sources` through the Supabase API, outside the trigger's usual run window if possible. If it fails on the lock timeout, retry.
3. Verify: constraints, columns, view options, anon-key select returns nothing, `list_migrations` shows both versions.
4. Regenerate `database.types.ts` (`pnpm db:types`), finish the UI, run `pnpm check` and `pnpm build`, and deploy.

**Rollback**: the UI is reverted by redeploying the previous commit. The schema is left in place: every addition is optional for the trigger and ignored by the old UI, except that the old edit form can't save sources with new access methods. Reverting the schema is not planned, because the trigger may already have written rows that use the new values.
