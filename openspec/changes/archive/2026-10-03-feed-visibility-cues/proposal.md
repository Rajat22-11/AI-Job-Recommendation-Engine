## Why

Three things in the feed are hard to read today:
- Skipping a job makes it vanish with nothing showing that it is only hidden.
- "Salary unknown" mixes "the posting doesn't say" with "it says, but couldn't be compared".
- Nothing tells the user whether Apply goes to the employer or to a job board.

The "New today (N)" badge also counts jobs its own link then filters out (saved, skipped and low-fit jobs), so the number and the list disagree.

## What Changes

- A "N skipped jobs hidden · Show" line appears when the current filters hide skipped jobs that would otherwise match. A skipped job's card offers **Restore** in place of the disabled Skip.
- Salary is split into **not disclosed** (no salary text or figures) and **not compared** (salary given, but `salary_meets_min` is empty). Each is shown distinctly on cards and is filterable with `salary=not_disclosed` and `salary=unparsed`. `salary=unknown` keeps working as the union, for old links.
- Apply shows an **Employer site** or **Job board** badge from `jobs.apply_url_kind` (added by `auto-learned-sources`).
- "New today (N)" counts exactly what its link shows: active jobs first seen in the last 24 hours with status `new`, at any fit score. The link opens that view on its own (`/?seen=24h&status=new&fit=0`) instead of mixing it into the current filters.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `job-feed`: job card contents (salary states, link-kind badge), apply links, URL-driven filters (salary values), New today preset, quick triage (Restore); new requirement for the hidden-skipped notice.

## Impact

- **Depends on** `auto-learned-sources` for `job_feed.apply_url_kind`. Everything else works on the current schema.
- **Code**: `src/lib/feed/params.ts`, `src/lib/feed/chips.ts`, `src/lib/db/queries/feed.ts`, `src/lib/db/jobs.ts`, `src/lib/applications.ts`, `src/components/job-parts.tsx`, `src/components/triage-actions.tsx`, `src/components/filter-panel.tsx`, `src/app/(app)/page.tsx`.
- Tracker counts are unaffected: they read `applications` directly.
- **Archive prerequisite**: `implement-ui` must be archived first so `job-feed` exists under `openspec/specs/`.
