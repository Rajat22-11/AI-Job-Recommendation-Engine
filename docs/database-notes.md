# Database notes

Facts read from the live Supabase project "Jobs Recommendation Engine" (`ooqayggwtfhrqhsovbhd`) on 2026-11-08 with read-only queries against `pg_constraint`, `pg_indexes` and the tables. Re-check these before changing the persistence code.

## Allowed values (check constraints)

| Column | Allowed values | How the pipeline maps to it |
|---|---|---|
| `source_runs.status` | `ok`, `partial`, `needs_login`, `captcha`, `error`, `skipped` | succeeded → `ok`, partial → `partial`, failed → `error`, skipped → `skipped`. A blocked source maps by block kind: a sign-in wall → `needs_login`, a challenge page → `captcha`, an IP or HTTP block (403) → `error` with the reason in the message. The UI shows "Log in to X in Chrome before the next run" for `needs_login` and `captcha`, so those two are used only when logging in could help |
| `source_run_queries.status` | `done`, `pending`, `rate_limited`, `failed`, `skipped` | not written by the pipeline |
| `sources.access_method` | `auto`, `connector`, `public_scrape`, `browser_session`, `api`, `rss` | open_api, ats_board, linkedin_profile_posts → `api`; jobspy_board → `connector`; rss_feed → `rss`; web_page → `public_scrape`. Set on new rows and kept current on existing ones. The UI shows "template not applicable" for `connector`, `api` and `rss` |
| `sources.template_status` | `unverified`, `verified`, `failed` | not written |
| `jobs.location_bucket` | `pune`, `mumbai`, `gujarat`, `remote_india`, `remote_international`, `other` | see `processing.location_buckets` in settings |
| `jobs.role_track` | `java_backend`, `ml_ai`, `data`, `full_stack`, `other` | see `processing.role_tracks` in settings |
| `jobs.work_mode` | `onsite`, `hybrid`, `remote` | |
| `jobs.apply_url_kind` | `employer`, `board` | |
| `jobs.fit_score` | 0 to 5 | pipeline writes 1 to 5 |

`runs.status` has no check constraint; existing values are `running` (17 rows, including abandoned runs) and `partial` (12).
`jobs.employment_type` has no constraint; existing values are `full_time` (56), `full-time` (13), `fulltime` (3). The pipeline writes `full_time`, `part_time`, `contract`, `internship`.

## Keys and uniqueness

- `jobs.dedupe_key` has a UNIQUE constraint (`jobs_dedupe_key_key`). No migration is needed for it.
- `job_sources.url` is UNIQUE (`job_sources_url_key`); there is no unique `(job_id, source_id)`. Links are upserted on `url`.
- `job_sources.source_id`, `source_runs.source_id` and `source_run_queries.source_id` reference `sources(id)`, so a source must exist in `sources` before its first run row. The registry sync runs first for this reason.
- `runs.run_id` is the primary key and has no default. The pipeline generates a UUID client-side; migration `001` adds a default for other writers.
- There is no table for seen LinkedIn posts; migration `002` adds one.

## Existing dedupe key format

Sample (20 most recent jobs):

| company | title | location | dedupe_key |
|---|---|---|---|
| Reliance Jio Infocomm Limited | Software Development Engineer I | Mumbai, Maharashtra | `reliance jio infocomm limited\|software development engineer i\|mumbai` |
| JPMorganChase | Software Engineer II - Java - Springboot, React, RDBMS, Kubernetes | Mumbai, Maharashtra | `jpmorganchase\|software engineer ii java springboot react rdbms kubernetes\|mumbai` |
| General Mills | Associate D&T Analyst - AI & Automation | Powai, Mumbai, Maharashtra | `general mills\|associate dt analyst ai automation\|mumbai` |
| Barclays | Software Engineer - I (Java/J2EE developer) | Pune, India | `barclays\|software engineer i java j2ee developer\|pune` |
| Priceline.com | Associate Software Engineer | Mumbai, Maharashtra | `priceline.com\|associate software engineer\|mumbai` |
| PradeepIT Consulting Services | Junior Java Developer | India (Remote) | `pradeepit consulting services\|junior java developer\|remote` |
| Amazon | Software Development Engineer I | Pune / Bengaluru / Hyderabad / Chennai / Delhi | `amazon\|software development engineer i\|pune` |

Rules inferred:

- **company:** lowercased and trimmed; punctuation such as `.` is kept (`priceline.com`).
- **title:** lowercased; `/` becomes a space; `&`, `-`, `|`, `(`, `)`, `,`, `+` and other punctuation are removed; whitespace is collapsed.
- **location:** `remote` when the location says remote; otherwise the first known city in the text (`Powai, Mumbai` → `mumbai`, `Pune / Bengaluru` → `pune`); otherwise the first comma-separated part.

Two of the 20 samples cannot be reproduced by rules because the routine's model edited them by hand:
- `tata communications|junior software developer|pune`: a parenthetical was dropped from the title.
- `hiring tag private limited|java developer|pune`: the company was renamed from "Hiring Tag (client)".

Such jobs may be stored once more under the rule-based key. This is accepted.

## Who owns what (the UI repository's rules)

The UI project (`D:\Projects\AI Job Recommendation UI`) owns the schema and the owner's edits. It reads these tables with the service role and writes `search_config`, and the `sources` columns name, base_url, requires_login, enabled, notes, and (through Advanced override) access_method and the search URL template.

- This pipeline therefore never overwrites `enabled`, `name`, `base_url` or notes on an existing source. It keeps `access_method` in step with how the source is really fetched.
- Schema changes belong in the UI repo's `supabase/migrations/` (additive, idempotent, `lock_timeout`, applied through the migration API so history matches). `migrations/001` and `002` in this repo follow those rules. Both were applied to the live database on 2026-11-09 through the migration API (history: `runs_run_id_default`, `linkedin_seen_posts`) and verified by querying the schema; the files stay here and the UI repo is untouched. Run `pnpm db:types` in the UI repo if it should see the new table.
- The UI's run page reads `runs.config_snapshot` as `{search_config: {...}, sources: [...]}`, which is the shape this pipeline writes.
- The UI feed filters by `job_sources.source_id` through the `links` column of `job_feed`, so source ids must match `^[a-z0-9_-]{2,40}$`.

## Spike results

- JobSpy from the owner's PC (2026-11-08): Indeed works; Naukri blocked (reCAPTCHA, HTTP 406); Glassdoor blocked (HTTP 403). Naukri now runs through Apify. Render run: not yet done (task 17.3).
- Apify LinkedIn posts (2026-11-08, live): 6 posts fetched across 2 profiles, 4 hiring, all links resolved; the actor works with the parser as written.
