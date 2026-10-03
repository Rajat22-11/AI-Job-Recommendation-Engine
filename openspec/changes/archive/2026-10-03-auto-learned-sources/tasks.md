## 1. Migration files

- [x] 1.1 Create `supabase/migrations/20261002190056_init_job_aggregator_schema.sql` from `supabase_migrations.schema_migrations.statements` for that version, with a header comment saying it is the applied baseline
- [x] 1.2 Write the `auto_learned_sources` migration SQL (design §2): lock and statement timeouts; `sources` columns, constraints, `access_method` nullable with default `auto`, template backfill; `source_runs` `partial` status and `config_snapshot`; `runs` and `source_run_queries` with RLS on, no policies, and the `(source_id, run_id)` index; `jobs.apply_url_kind` with backfill; `job_feed` recreated `WITH (security_invoker = true)` with `apply_url_kind` last
- [x] 1.3 Dry-run the SQL in a rolled-back transaction (`BEGIN; … ROLLBACK;`) through the Supabase API, then run it twice in one rolled-back transaction to confirm it is idempotent
- [x] 1.4 Apply the migration through the Supabase API, and name the file `supabase/migrations/<recorded version>_auto_learned_sources.sql` to match `list_migrations`
- [x] 1.5 Verify the live schema: constraint definitions, column defaults, `job_feed` reloptions include `security_invoker=true`, 4 sources backfilled as manual + verified, `indeed` unchanged except the defaults, and an anon-key select on `runs`, `source_run_queries` and `job_feed` returns no rows
- [x] 1.6 Run `pnpm db:types` and commit the regenerated `src/lib/db/database.types.ts`

## 2. Domain and pure logic

- [x] 2.1 Extend `src/lib/db/domain.ts`: access methods `auto`, `api`, `rss` with labels; run status `partial`; template statuses, template origins, query statuses, apply-link kinds, each with labels
- [x] 2.2 Add `effectiveRunStatus(status, message)` to `src/lib/sources.ts`, with tests for `partial`, an `ok` + `PARTIAL:` message (any case), and pass-through
- [x] 2.3 Add `templateState(source)` with tests for not applicable (connector, api, rss), waiting, waiting to verify, verified, failed, and disabled + waiting
- [x] 2.4 Add `deriveSourceId(name, baseUrl, takenIds)` with tests for a plain name, punctuation, the 40-character cut, the host fallback (drops `www.`), suffixes `-2`…`-9`, and exhaustion
- [x] 2.5 Add `sameSiteSource(baseUrl, sources)` (host match ignoring `www.` and case) with tests
- [x] 2.6 Add `queryCoverage(rows)` → `{ done, total, unfinished[] }` with tests, and `EMPTY_RUN_WARNING_THRESHOLD = 3` with a `emptyRunWarning(n)` helper

## 3. Data access and actions

- [x] 3.1 Extend `getSourcesWithRuns` to include each source's latest-run query rows from `source_run_queries` (parallel, by source and run id)
- [x] 3.2 Rewrite `createSource`: accept only name, base URL, requires login and notes; derive the id; reject same-site sources; insert with `access_method='auto'`, `enabled=true`, `template_status='unverified'`; retry once with the next suffix on a unique violation
- [x] 3.3 Rewrite `updateSource`: write only the plain fields; for the override, compare against the hidden originals and write `access_method` and template fields only when changed, validating a changed template with `templateError` (design §5)
- [x] 3.4 Add the `relearnTemplate` Server Action: assert the session, validate the id, update `template_status` to `unverified` only when the source's current state is verified or failed, then revalidate
- [x] 3.5 Add action tests (or pure-plan tests, following `applications.ts`) for the edit payload: an unchanged override writes no template keys, a changed template writes manual + unverified, a cleared template writes null origin + unverified

## 4. Settings UI

- [x] 4.1 Make the Add source form name, base URL, requires login and notes only, with a hint that the template is learned on the next run
- [x] 4.2 Edit source form: plain fields plus a collapsed "Advanced override" (access method with all six values, template with placeholder help and example, hidden originals); id read-only
- [x] 4.3 Show the template state line in each source's summary row on Settings

## 5. Sources page

- [x] 5.1 Template state block per source: the not applicable / waiting / waiting to verify / disabled texts, verified (read-only template, Learned/Manual, verified time), failed (reason or "No reason recorded")
- [x] 5.2 "Re-learn template" form button for verified and failed sources only (44px target, works without JavaScript)
- [x] 5.3 Show "Last success …"/"Never" and the empty-run warning badge when `consecutive_empty_runs` ≥ 3
- [x] 5.4 Use `effectiveRunStatus` for run badges: add the "Partial" label and warning tone, with a neutral raw-text fallback for unknown statuses
- [x] 5.5 Query coverage: "N of M queries done", plus a collapsed "Will resume on the next run" list (keyword, location, page, status, error), hidden when there are no rows
- [x] 5.6 Collapsed read-only `scrape_hints` (pretty JSON) when not empty
- [x] 5.7 Check the page at 360px wide: no horizontal scroll (long templates and URLs wrap)

## 6. Docs and project rules

- [x] 6.1 Update the `openspec/config.yaml` context: the app owns additive migrations in `supabase/migrations/` (RLS on, no policies, views `security_invoker`), replacing "never changes the schema"
- [x] 6.2 Update `README.md`: the add-source flow, template states, and how to write and apply a migration

## 7. Verification

- [x] 7.1 `pnpm check` and `pnpm build` pass
- [x] 7.2 Manual run against the live app: add a source by name + URL and see it waiting; Re-learn a verified source and see it as "Will be verified on the next run" with the template kept; edit only notes on a source with a learned template and confirm the template is unchanged in the database; legacy `PARTIAL:` runs show as Partial; the `indeed` template state shows "Not applicable"
