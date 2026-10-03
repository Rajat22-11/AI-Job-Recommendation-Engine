## Why

The daily trigger can now learn and verify a source's search URL template, resume interrupted searches, and record partial runs, but the database has nowhere to keep that state and the app still makes the user hand-write an id, access method and URL template for every new source. The trigger already detects these schema features at runtime and falls back when they are missing, so adding the schema and the matching Sources UI is all that stands between the user and "paste a URL, the next run figures it out".

## What Changes

- **BREAKING (project rule)**: the app now owns versioned, additive schema migrations in `supabase/migrations/`. This replaces the rule that the app never changes the schema. The existing init migration is committed as the baseline.
- One additive, idempotent migration, safe to apply while a run is in progress:
  - `sources`: `template_status`, `template_origin`, `template_verified_at`, `template_notes`, `consecutive_empty_runs`, `last_success_at`, `scrape_hints`; `access_method` accepts `auto`, `api`, `rss`, becomes nullable and defaults to `auto`; existing rows with a template are backfilled as manual and verified.
  - `source_runs`: status `partial`, optional `config_snapshot`.
  - New tables `runs` and `source_run_queries` with RLS enabled and no policies, like every other table.
  - `jobs.apply_url_kind` (`employer` | `board`, backfilled `board`), exposed through `job_feed`, which keeps `security_invoker`.
- Add source takes only a name and a base URL (plus requires-login and notes). The id is derived, and the source is saved as `auto` with no template, waiting to be learned on the next run.
- Edit source no longer sends the template or access method unless the user opens an "Advanced override". The override marks the template as manual and unverified.
- The Sources page shows the template state (waiting, verified, failed with reason, or not applicable), the learned template read-only, last success, a warning after repeated empty runs, partial runs (including legacy `PARTIAL:` messages), query coverage for the latest run, and a "Re-learn template" action that asks the trigger to re-verify.

Feed changes (`apply_url_kind` badge and others) and run history are separate follow-up changes: `feed-visibility-cues` and `run-history`.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `data-access`: the "existing schema is used unchanged" rule is replaced by versioned additive migrations; domain value sets gain the new access methods, run status, template states, query states and apply-link kinds.
- `source-health`: the sources overview adds template state, last success, empty-run warnings, partial runs and query coverage; new Re-learn action.
- `search-settings`: Add source becomes name + URL only; Edit source protects learned templates behind an advanced override; template validation applies only to manual overrides.

## Impact

- **Database** (Supabase project "Jobs Recommendation Engine"): one new migration; no data loss; existing trigger keeps working before and after.
- **New**: `supabase/migrations/` (baseline + this migration).
- **Code**: `src/lib/db/database.types.ts` (regenerated), `src/lib/db/domain.ts`, `src/lib/sources.ts`, `src/lib/db/queries/sources.ts`, `src/lib/actions/settings.ts`, `src/app/(app)/settings/*`, `src/app/(app)/sources/page.tsx`, `src/lib/templates.ts`.
- **Docs**: `openspec/config.yaml` context and `README.md` describe the new schema ownership.
- **Prerequisite for archive**: `implement-ui` and `improvise-ui-change` must be archived first so the modified capabilities exist under `openspec/specs/`.
