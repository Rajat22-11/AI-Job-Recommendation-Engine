## ADDED Requirements

### Requirement: Schema changes through versioned migrations
Every schema change the app depends on SHALL be a SQL migration file in `supabase/migrations/`, named `<version>_<name>.sql`, whose version matches the entry recorded in the database's migration history. The repository MUST contain the existing init migration as its baseline. Migrations MUST be additive and idempotent: running one twice leaves the schema unchanged, and no existing column, row or constraint value that a running trigger relies on is removed or narrowed. Every table MUST keep Row Level Security enabled with no policies, so only the server-side service role can read or write it. Views MUST keep `security_invoker = true`.

#### Scenario: Migration applied twice
- **WHEN** the auto-learned-sources migration is run against a database that already has it
- **THEN** it succeeds and the schema is unchanged

#### Scenario: Anonymous access to a new table
- **WHEN** a request with the project's anon key selects from `runs` or `source_run_queries`
- **THEN** it returns no rows

#### Scenario: Anonymous access through the view
- **WHEN** a request with the anon key selects from `job_feed` after the view is recreated
- **THEN** it returns no rows

#### Scenario: Applied while the trigger is running
- **WHEN** the migration is applied while the trigger is inserting `source_runs` rows with existing statuses
- **THEN** both the migration and the trigger's inserts succeed, or the migration fails on its lock timeout without blocking the trigger and can be retried

## MODIFIED Requirements

### Requirement: Domain values match database constraints
The app SHALL accept and offer only the values allowed by the database CHECK constraints:
- Application status: `saved`, `applied`, `interview`, `offer`, `rejected`, `skipped`, plus the derived feed value `new`.
- Role track: `java_backend`, `ml_ai`, `data`, `full_stack`, `other`.
- Location bucket: `pune`, `mumbai`, `gujarat`, `remote_india`, `remote_international`, `other`.
- Work mode: `onsite`, `hybrid`, `remote`.
- Source access method: `auto`, `connector`, `public_scrape`, `browser_session`, `api`, `rss`.
- Source run status: `ok`, `partial`, `needs_login`, `captcha`, `error`, `skipped`.
- Source template status: `unverified`, `verified`, `failed`.
- Source template origin: `manual`, `auto`.
- Run query status: `done`, `pending`, `rate_limited`, `failed`, `skipped`.
- Apply link kind: `employer`, `board`.

Each value MUST have a human-readable label, for example `ml_ai` → "ML / AI", `remote_india` → "Remote (India)", `auto` → "Auto-detect" and `rate_limited` → "Rate limited". A value read from the database that the app does not recognise MUST be shown as its raw text instead of causing an error.

#### Scenario: Invalid value in a URL
- **WHEN** a feed request supplies `status=archived` or `track=frontend`
- **THEN** that filter value is ignored and the feed renders without an error

#### Scenario: Invalid value in a form
- **WHEN** a form submission supplies an application status outside the allowed set
- **THEN** it is rejected with a validation message, no data changes, and no database error reaches the user

#### Scenario: Unrecognised value from the database
- **WHEN** a `source_runs` row has a status the app does not list
- **THEN** the sources page shows that status as raw text with a neutral badge

## REMOVED Requirements

### Requirement: Existing schema is used unchanged
**Reason**: The trigger's new template learning, run tracking and query resumption need columns and tables the original schema lacks, and the trigger has no repository of its own to hold migrations.
**Migration**: Schema changes are made only through the versioned, additive migrations described in "Schema changes through versioned migrations".
