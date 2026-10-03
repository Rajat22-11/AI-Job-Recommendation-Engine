## Purpose

Defines how the app reads and writes the existing Supabase database: only on the server, with a privileged key that never reaches the browser, and with consistent types and India-time date rules.

## ADDED Requirements

### Requirement: Server-only database access
All database reads and writes SHALL happen on the server, using `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. The service role key, and any other Supabase credential, MUST never be sent to the browser: not in JavaScript bundles, HTML, serialized props or response headers. No environment variable with the `NEXT_PUBLIC_` prefix may hold a Supabase value. The browser MUST never talk to Supabase directly.

#### Scenario: Key absent from client output
- **WHEN** the production build's client assets and a rendered page's HTML are searched for the service role key value and for the Supabase project host
- **THEN** neither is found

#### Scenario: No direct browser calls
- **WHEN** the feed is used, including quick actions, while browser network traffic is recorded
- **THEN** no request goes to the Supabase host

### Requirement: Existing schema is used unchanged
The app SHALL work with the existing tables, the `job_feed` view and their constraints as they are. It MUST NOT create, alter or drop tables, views, functions, policies or constraints. Row Level Security stays enabled with no public policies.

#### Scenario: Schema unchanged after deploy
- **WHEN** the app has been deployed and used
- **THEN** the database schema matches its state before this change

### Requirement: Domain values match database constraints
The app SHALL accept and offer only the values allowed by the database CHECK constraints:
- Application status: `saved`, `applied`, `interview`, `offer`, `rejected`, `skipped`, plus the derived feed value `new`.
- Role track: `java_backend`, `ml_ai`, `data`, `full_stack`, `other`.
- Location bucket: `pune`, `mumbai`, `gujarat`, `remote_india`, `remote_international`, `other`.
- Work mode: `onsite`, `hybrid`, `remote`.
- Source access method: `connector`, `public_scrape`, `browser_session`.
- Source run status: `ok`, `needs_login`, `captcha`, `error`, `skipped`.

Each value MUST have a human-readable label, for example `ml_ai` → "ML / AI" and `remote_india` → "Remote (India)".

#### Scenario: Invalid value in a URL
- **WHEN** a feed request supplies `status=archived` or `track=frontend`
- **THEN** that filter value is ignored and the feed renders without an error

#### Scenario: Invalid value in a form
- **WHEN** a form submission supplies an application status outside the allowed set
- **THEN** it is rejected with a validation message, no data changes, and no database error reaches the user

### Requirement: India Standard Time for dates
Calendar dates the app writes or shows SHALL be computed in `Asia/Kolkata`, regardless of the server's time zone. This covers "today" for `applied_on`, relative times such as "3d ago", the "New" window, and displayed dates.

#### Scenario: Applying just after midnight IST
- **WHEN** a job is marked applied at 00:30 IST on 2026-10-04 (which is 19:00 UTC on 2026-10-03)
- **THEN** `applied_on` is stored as 2026-10-04

### Requirement: Source names resolved from ids
Wherever a job's source appears, the app SHALL show the source's `name` from `sources`, not its id. A link whose source id has no matching row MUST fall back to the id.

#### Scenario: Link to a known source
- **WHEN** a job's `links` contains `{source: "naukri", url: …}` and source `naukri` is named "Naukri"
- **THEN** the badge and link text read "Naukri"

#### Scenario: Unknown source id
- **WHEN** a link's source id has no row in `sources`
- **THEN** the badge shows the raw id and the link still works
