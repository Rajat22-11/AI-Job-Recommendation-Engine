## 1. Preconditions

- [x] 1.1 Confirm the `auto-learned-sources` migration is applied (`job_feed` has `apply_url_kind`) and `database.types.ts` includes it

## 2. Salary states

- [x] 2.1 Add `salaryState(job)` (`not_disclosed | compared | not_compared`) with tests: blank and whitespace text, figures without text, text with null `salary_meets_min`, true/false comparisons
- [x] 2.2 Extend `SALARY_FILTERS` with `not_disclosed` and `unparsed`, keeping `unknown`; update parse and serialize tests, including that `salary=unknown` round-trips
- [x] 2.3 Add the `not_disclosed` and `unparsed` query branches in `filteredFeed` (design Â§1)
- [x] 2.4 Filter panel offers Any / Meets minimum / Not disclosed / Not compared, and shows "Salary unknown" when the URL holds `unknown`. Add chip labels and tests for each value
- [x] 2.5 Card salary rendering per state: "Salary not disclosed" badge, salary text plus "Meets min", and salary text plus the "not compared" note

## 3. Link kind

- [x] 3.1 Map `apply_url_kind` in `toFeedJob` to `applyUrlKind` (`employer | board | null`)
- [x] 3.2 Show the "Employer site" / "Job board" badge next to Apply on the card and the detail page

## 4. Skipped visibility

- [x] 4.1 Add a `restore` quick action planned as delete, with tests in `applications.test.ts`
- [x] 4.2 `TriageActions`: a skipped card shows "Restore" (44px target, works without JavaScript) in place of the disabled Skip, with Undo as for the other actions
- [x] 4.3 Add `countHiddenSkipped(filters)` (returns null when not applicable) and run it in the feed page's `Promise.all`
- [x] 4.4 Render "N skipped job(s) hidden Â· Show" under the result count, with "Show" adding `skipped` to the status filter. Add tests for the pure href and plural text helpers

## 5. New today

- [x] 5.1 `countNewToday` counts only `app_status = 'new'`
- [x] 5.2 Point the "New today" link at the fixed preset `/?seen=24h&status=new&fit=0`, and update the related params and chips tests

## 6. Verification

- [x] 6.1 `pnpm check` and `pnpm build` pass
- [x] 6.2 Manual check against live data: the default view shows "1 skipped job hidden"; Show reveals it with Restore; Restore + Undo round-trip; the three seeded jobs show "Salary not disclosed"; the New today count equals the number of jobs its link lists; Tracker counts are unchanged; 360px width has no horizontal scroll
