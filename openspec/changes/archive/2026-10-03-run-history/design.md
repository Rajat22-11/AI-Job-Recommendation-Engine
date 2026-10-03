## Context

- After `auto-learned-sources`, run data lives in two places: `runs` (one row per trigger run, possibly missing for older or fallback runs) and `source_runs` (one row per source per run, always written, `run_id` uuid, indexed on `(source_id, started_at desc)` only).
- Today there are 21 `source_runs` rows across 5 run ids and no `runs` rows. The trigger runs daily, so 30 runs is about a month and at most a few hundred `source_runs` rows.
- Project rules: minimal client JS, IST for every date (`src/lib/dates.ts`), and no new dependencies unless needed.

## Goals / Non-Goals

**Goals:**
- Older runs (with no `runs` row) appear the same as new ones, just with less detail.
- All grouping, status derivation, trend bucketing and snapshot diffing are pure functions with unit tests.

**Non-Goals:**
- Pagination beyond 30 runs, filtering runs, or deleting runs.
- Charts with interaction (hover, zoom). No chart library.
- Editing or re-applying an old config snapshot.

## Decisions

### 1. Merge in the app, not in SQL

There are two parallel queries:
- `source_runs` where `started_at` is in the last 45 days, newest first, at most 1000 rows
- `runs` ordered by `started_at` desc, limit 30

`groupRuns(sourceRuns, runs)` merges them by `run_id`, derives times and status as the spec says, sorts newest first, and keeps 30. The trend uses the same `source_runs` rows, so the page makes 2 queries plus the current config and source names.

*Alternative*: a SQL view or RPC that groups by `run_id`. Rejected: it adds schema the trigger doesn't need, and the row counts are tiny.

### 2. Trend as a server-rendered table with CSS bars

`newJobsTrend(sourceRuns, today, days = 14)` returns rows of `{ date, perSource: Map, total | null }`. IST dates come from the existing date helpers. Each bar is a `div` whose width is `total / maxTotal`, styled with theme tokens and no JavaScript. The table is the accessible form of the chart, so no separate text alternative is needed. Sources appear in name order and get a column only if they had a run in the window, which keeps the table narrow on phones.

*Alternative*: inline SVG small multiples per source. Rejected for now: more code, and harder to read at 360px with 5+ sources.

### 3. Snapshot diff on known fields only

The trigger writes snapshots as `{ "search_config": { ...settings row }, "sources": [...] }` (seen on its first run after the migration). The settings are read from `search_config` when present, otherwise from the top level. Other top-level keys (such as `sources`) and unknown settings keys are shown as JSON, and the row `id` is ignored. When a snapshot has none of the known fields, the run says "No settings to compare" rather than "Same as current settings".

`diffConfig(snapshot, current)` compares the six known fields. Lists are compared as case-insensitive sets, matching how Settings normalizes them, and numbers numerically. The result is a list of labels for the fields that differ. Unknown keys are shown but never compared, because the trigger may add fields the app doesn't understand.

### 4. "Last used by run" reads the newest start time from both tables

`getLatestRun()` selects the newest `started_at` and `run_id` from `runs` and from `source_runs` (limit 1 each), in parallel, and takes the later one. The comparison with `search_config.updated_at` happens in the server component. After a save, the client form compares the returned `savedAt` with the run start it received as a prop, so the "Changed after this run" note shows up without a reload.

This assumes the trigger reads the config when the run starts. If it reads later, a change made in the first minutes of a run could be reported as "after this run" even though the run used it. That's acceptable: the snapshot on `/runs` shows what was actually used.

### 5. Anchors

Each run on `/runs` has `id="run-<run_id>"`, so Settings can link straight to it.

## Risks / Trade-offs

- [Run with mixed timestamps across both tables] → The `runs` row wins for times and status. `source_runs` totals are always summed from source rows, so the numbers match `/sources`.
- [45-day / 1000-row window cuts off a run's source rows] → At daily cadence and about 6 sources this is far below the limit. If it's hit, the oldest listed run may show partial totals, which is acceptable for a history view.
- [Unrecognised `runs.status` values] → Shown as raw text with a neutral badge, following the data-access rule.
