## 1. Preconditions

- [x] 1.1 Confirm the `auto-learned-sources` migration is applied (`runs` table, `source_runs.config_snapshot`) and the generated types include them

## 2. Pure logic

- [x] 2.1 `groupRuns(sourceRuns, runs)` in `src/lib/runs.ts`: merge by `run_id`, derive times, status (OK / Needs attention / `runs.status`) and totals, newest first, at most 30. Tests cover runs-only, source_runs-only, both, and the effective Partial status
- [x] 2.2 `newJobsTrend(sourceRuns, today, 14)`: IST day buckets, per-source sums, null for days without runs, and only the sources active in the window. Tests include the UTC→IST day boundary
- [x] 2.3 `diffConfig(snapshot, current)` and `snapshotFields(snapshot)`: the six known fields with Settings labels, list comparison as case-insensitive sets, and unknown keys passed through. Tests included
- [x] 2.4 `lastUsedNote(latestRun, updatedAt)` returning the used-by text and the changed-after flag, with tests for no runs, unchanged, and changed after

## 3. Data access

- [x] 3.1 `src/lib/db/queries/runs.ts`: `getRunHistory()` (two parallel queries, design §1) and `getLatestRun()` (design §4)

## 4. Runs page

- [x] 4.1 `src/app/(app)/runs/page.tsx` (session required, title "Runs"): the run list with time, duration, status badge, totals and summary, `id="run-<run_id>"` anchors, and "No runs yet"
- [x] 4.2 Per-run collapsed source results, using the Sources page's run badge (shared component extracted from `sources/page.tsx`)
- [x] 4.3 Per-run collapsed config snapshot with the "Same as" / "Differs from current settings" line, or "No config snapshot recorded"
- [x] 4.4 14-day trend table with CSS bars, "—" for empty days, and its own horizontal scroll container
- [x] 4.5 Add "Runs" to the main navigation, checking the nav still fits at 360px

## 5. Settings

- [x] 5.1 Settings page loads `getLatestRun()` and passes the run id and start time to `SearchConfigForm`
- [x] 5.2 Show "Last used by run … at …" (linked to `/runs#run-<id>`), the changed-after note (also after a save, without a reload), or "Not used by any run yet"

## 6. Verification

- [x] 6.1 `pnpm check` and `pnpm build` pass
- [x] 6.2 Manual check against live data: the 5 existing runs appear with source results and "No config snapshot recorded"; trend totals match the summed `jobs_new` from SQL for each IST day; saving Settings shows the changed-after note; the page has no page-level horizontal scroll at 360px
