## Context

- The feed builds one PostgREST query in `filteredFeed` (`src/lib/db/queries/feed.ts`). Separate `.or()` calls are ANDed. The salary filter today is `meets` → `salary_meets_min = true`, `unknown` → `salary_meets_min IS NULL`.
- `countNewToday` counts active jobs first seen in the last 24h at any status and fit score. The "New today" link merges `seen24h` + `status=new` into the **current** filters, keeping `fit ≥ 3`, so the count and the list can differ.
- Skip, Save/Unsave and Undo go through `quickAction` → `quickActionPlan` (`src/lib/applications.ts`). `unsave` already plans a delete. The Skip button is just disabled on a skipped card.
- `job_feed.apply_url_kind` comes from `auto-learned-sources`.

## Goals / Non-Goals

**Goals:**
- One shared definition of each salary state, used by both the card and the filter, so they can't disagree.
- No change to Tracker counts or to the default feed's result set.

**Non-Goals:**
- Changing how the trigger fills `salary_meets_min` or `apply_url_kind`.
- A separate "skipped" page. The Tracker's Skipped column already exists.

## Decisions

### 1. Salary state: one pure classifier, mirrored filter expressions

`salaryState(job)` returns `not_disclosed | compared | not_compared`:
- `not_disclosed`: `salary_text` is null or blank, and both LPA figures are null
- `compared`: `salary_meets_min` is not null
- otherwise `not_compared`

The query side mirrors it:
- `not_disclosed`: `.or('salary_text.is.null,salary_text.eq.')`, plus `.is('salary_min_lpa', null)` and `.is('salary_max_lpa', null)`
- `unparsed`: `.is('salary_meets_min', null)`, plus `.or('salary_text.neq.,salary_min_lpa.not.is.null,salary_max_lpa.not.is.null')`
- `unknown`: unchanged

Whitespace-only `salary_text` counts as disclosed in SQL but not in the classifier. That's accepted: the trigger trims text, and a test pins the classifier to "trimmed empty = not disclosed".

*Alternative*: a generated column or view field `salary_state`. Rejected to keep this change UI-only. The migration surface lives in `auto-learned-sources`.

### 2. Hidden-skipped count is one extra head query

When `status !== 'all'` and it doesn't include `skipped`, run `filteredFeed({...filters, status: ['skipped']}, head: true)` in the same `Promise.all` as the page. The cost is one `count: exact` query on a small table. The "Show" link is `feedHref(filters, { status: [...filters.status, 'skipped'] })`.

### 3. Restore reuses the delete plan

Add `restore` to `QUICK_ACTIONS`, planned as `{ kind: 'delete' }`, which is the same as `unsave`. Undo already restores the exact previous row, notes included. `TriageActions` renders Restore in place of Skip when the optimistic status is `skipped`.

*Alternative*: set status back to `saved`. Rejected: Restore should undo the Skip, and a job that was skipped straight from `new` was never saved.

### 4. New today becomes a fixed preset

`countNewToday` adds `.eq('app_status', 'new')`. The link is the constant `/?seen=24h&status=new&fit=0`, built through `serializeFeedParams` so the URL stays canonical. The count no longer depends on the current filters, and the link doesn't inherit them.

### 5. Link-kind badge

`toFeedJob` maps `apply_url_kind` to `applyUrlKind: 'employer' | 'board' | null`, narrowed with `isOneOf`. The badge sits next to Apply, `success` tone for employer and neutral for board.

## Risks / Trade-offs

- [Deploying before `auto-learned-sources` is applied] → `apply_url_kind` would be missing from the view and the select would fail. Implement and deploy this change only after that migration is live (the tasks start with a check).
- [Old bookmarks with `salary=unknown`] → Still accepted, and shown as its own chip.
- [Restore drops notes on a skipped job] → The same trade-off as Unsave today. Undo brings them back for 5 seconds, and the detail page remains the place to edit notes.
