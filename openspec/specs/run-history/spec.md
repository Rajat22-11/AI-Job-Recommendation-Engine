# run-history Specification

## Purpose
Shows the history of the daily trigger's runs as a whole: what each run did per source, which search settings it used, and how many new jobs each source has produced per day, so drying-up sources and unapplied settings changes are visible.

## Requirements

### Requirement: Runs list
The page `/runs` SHALL be reachable from the main navigation and SHALL list the 30 most recent runs, newest first. A run is identified by `run_id`, and every `run_id` found in `runs` or in `source_runs` counts. Each run MUST show:
- its start time (relative and absolute in IST) and its duration when it has finished. Times come from the `runs` row when there is one, otherwise from the earliest `started_at` and latest `finished_at` of its `source_runs` rows
- its status: `runs.status` when a `runs` row exists. Otherwise "OK" when every source result is OK or Skipped, and "Needs attention" when any is not
- total jobs found and total new jobs across its source results
- `runs.summary` when present
- a collapsed list of per-source results: source name, status (Partial rules as on `/sources`), found, new and message

When there are no runs at all, the page MUST show "No runs yet".

#### Scenario: Run recorded only in source_runs
- **WHEN** run `r1` has 4 `source_runs` rows (3 `ok`, 1 `needs_login`) and no `runs` row
- **THEN** `/runs` lists `r1` with status "Needs attention" and the summed found and new counts

#### Scenario: Run with a runs row
- **WHEN** run `r2` has a `runs` row with status `completed` and summary "12 new jobs across 4 sources"
- **THEN** `r2` shows status "completed" and that summary

#### Scenario: Legacy partial result
- **WHEN** a source result in a run has status `ok` and message "PARTIAL: rate limited"
- **THEN** it is shown as Partial in that run's source list

### Requirement: Config snapshot per run
Each run SHALL show, collapsed, the search configuration it used: `runs.config_snapshot`, or else the first non-empty `source_runs.config_snapshot` of that run. Known fields (keywords, locations, excluded companies, minimum salary, maximum required experience, maximum job age) MUST be shown with the same labels as Settings, and any other keys as formatted JSON. Next to the snapshot, the run MUST say "Same as current settings", or "Differs from current settings:" followed by the labels of the known fields that differ. When no snapshot exists, it MUST say "No config snapshot recorded".

#### Scenario: Settings changed since the run
- **WHEN** a run's snapshot has minimum salary 8.2 and the current setting is 10
- **THEN** the run shows "Differs from current settings: Minimum salary (LPA)"

#### Scenario: Old run
- **WHEN** a run has no snapshot in `runs` or `source_runs`
- **THEN** it shows "No config snapshot recorded"

### Requirement: New jobs trend
`/runs` SHALL show new jobs per day for the last 14 days (IST calendar days, today included), per source and in total, summed from `source_runs.jobs_new` by the IST date of `started_at`. It MUST be rendered as a table, with one row per day (newest first), a column per source that has any run in the period, and a total column with a proportional bar. Days without any run MUST show "—" rather than 0. The table MUST fit a 360px-wide screen, scrolling inside its own container if needed, never the whole page.

#### Scenario: Daily totals
- **WHEN** on 3 Oct (IST) source `himalayas` found 4 new jobs and `wttj` 2, across two runs
- **THEN** the 3 Oct row shows 4 under Himalayas, 2 under WTTJ, and a total of 6

#### Scenario: Day without runs
- **WHEN** no run started on 30 Sep (IST)
- **THEN** the 30 Sep row shows "—" in every column

#### Scenario: Day boundary in IST
- **WHEN** a run started at 19:00 UTC on 2 Oct, which is 00:30 IST on 3 Oct
- **THEN** its new jobs count towards 3 Oct
