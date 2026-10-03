## Why

The Sources page only shows each source's last few runs. There is nowhere to see a whole daily run at once, whether new jobs per source are trending up or down, or which search settings a run actually used. Because of that, the user can't tell whether a settings change has taken effect yet or whether a source is slowly drying up.

## What Changes

- New `/runs` page, linked from the main navigation:
  - recent runs, newest first, built from `source_runs` grouped by `run_id` and enriched with the `runs` row when one exists (status, summary, config snapshot)
  - each run's per-source results
  - the config snapshot it used, with a note on which fields differ from the current settings
- A 14-day trend of new jobs per day per source (IST days), rendered on the server without a chart library.
- Settings shows "Last used by run … at …" next to "Last updated", and says when the settings changed after that run and so apply from the next one.

## Capabilities

### New Capabilities
- `run-history`: the runs page, per-run details, config snapshots, and the new-jobs trend.

### Modified Capabilities
- `search-settings`: adds the "last used by run" indicator to the search configuration form.
- `app-hosting`: the navigation gains a "Runs" link.

## Impact

- **Depends on** `auto-learned-sources` for the `runs` table and `source_runs.config_snapshot`. Runs from before that change still appear, built from `source_runs` only and without a snapshot.
- **Code**: new `src/app/(app)/runs/page.tsx`, `src/lib/db/queries/runs.ts`, `src/lib/runs.ts` (pure grouping, trend and diff logic); changes to `src/components/nav-links.tsx`, `src/app/(app)/settings/page.tsx` and `forms.tsx`.
- No new dependencies.
