## MODIFIED Requirements

### Requirement: Sources overview
The page `/sources` SHALL list every source with:
- name, base URL and access method label
- whether it requires login
- its enabled state
- its template state (see "Template learning state")
- when it last succeeded (`last_success_at`, relative and absolute in IST), or "Never" when empty
- its latest run: status, jobs found, new jobs, start time (relative and absolute in IST), duration when it has finished, and message

A source with no runs MUST show "No runs yet". Each source MUST also show its 5 most recent runs in a collapsed section.

#### Scenario: Latest run shown
- **WHEN** source "Naukri" last ran 2 hours ago with status `ok`, 40 found and 6 new
- **THEN** its row shows OK, 40 found, 6 new, and "2h ago"

#### Scenario: Never run
- **WHEN** a source has no `source_runs` rows
- **THEN** its row shows "No runs yet"

#### Scenario: Last success
- **WHEN** a source's `last_success_at` is 3 days ago and its latest run failed
- **THEN** its row shows the failed latest run and "Last success 3d ago"

## ADDED Requirements

### Requirement: Template learning state
Each source SHALL show exactly one template state:
- **Not applicable**: `access_method` is `connector`, `api` or `rss`. These sources do not use URL templates, whatever `template_status` says.
- **Waiting**: `template_status` is `unverified` and the source has no template. Reads "Waiting for first run. The template will be learned automatically."
- **Waiting to verify**: `template_status` is `unverified` and a template exists. Reads "Will be verified on the next run."
- **Verified**: `template_status` is `verified`. Shows the template read-only, whether it was learned or set manually (`template_origin`), and when it was verified.
- **Failed**: `template_status` is `failed`. Shows "Couldn't learn the template" and the reason from `template_notes`, or "No reason recorded" when it is empty.

A disabled source in a waiting state MUST instead read "Disabled. The template won't be learned until the source is enabled." `scrape_hints`, when not empty, MUST be shown read-only in a collapsed section.

#### Scenario: Newly added source
- **WHEN** a source was just added with only a name and base URL
- **THEN** it shows "Waiting for first run. The template will be learned automatically."

#### Scenario: Connector source
- **WHEN** source `indeed` has access method `connector` and `template_status` `unverified`
- **THEN** its template state reads "Not applicable" and no Re-learn action is offered

#### Scenario: Learning failed
- **WHEN** a source has `template_status` `failed` and `template_notes` "Search results load only after login"
- **THEN** it shows "Couldn't learn the template" and that reason

#### Scenario: Learned template
- **WHEN** the trigger verified a learned template yesterday
- **THEN** the template is shown as read-only text, labelled "Learned", with "Verified 1d ago"

### Requirement: Re-learn template
A source in the Verified or Failed state SHALL offer a "Re-learn template" action. It MUST set `template_status` to `unverified` and change nothing else: the template, its origin and its notes are kept, so the trigger re-verifies the existing template on its next run. The action MUST work without client-side JavaScript and MUST NOT be offered for sources whose template state is Not applicable or already waiting.

#### Scenario: Re-verify a template
- **WHEN** the user activates "Re-learn template" on a verified source
- **THEN** `template_status` is `unverified`, `search_url_template` is unchanged, and the source shows "Will be verified on the next run."

### Requirement: Empty-run warning
A source whose `consecutive_empty_runs` is 3 or more SHALL show a warning: "No jobs found in the last N runs", with N taken from `consecutive_empty_runs`. Below 3 no warning is shown.

#### Scenario: Three empty runs
- **WHEN** an enabled source has `consecutive_empty_runs` 3
- **THEN** it shows "No jobs found in the last 3 runs"

### Requirement: Partial runs
A run SHALL be shown as "Partial", with a warning tone, when its status is `partial`, or when its status is `ok` and its message starts with `PARTIAL:` (ignoring case). Partial runs MUST NOT trigger the login-needed banner.

#### Scenario: Legacy partial message
- **WHEN** a run has status `ok` and message "PARTIAL: 2 of 6 queries rate limited"
- **THEN** it is shown as Partial, with the full message

#### Scenario: Partial status
- **WHEN** a run has status `partial`
- **THEN** it is shown as Partial

### Requirement: Query coverage for the latest run
When the latest run of a source has rows in `source_run_queries`, the source SHALL show "N of M queries done", where M counts all of that run's queries and N those with status `done`. Queries with status `pending`, `rate_limited` or `failed` MUST be listed in a collapsed section with keyword, location, page, status and error, under the heading "Will resume on the next run". When the latest run has no query rows, this section MUST be omitted.

#### Scenario: Interrupted run
- **WHEN** the latest run planned 6 queries, 4 are `done`, 1 `rate_limited` and 1 `pending`
- **THEN** the source shows "4 of 6 queries done" and lists the 2 unfinished queries under "Will resume on the next run"

#### Scenario: Run without query details
- **WHEN** the latest run has no `source_run_queries` rows
- **THEN** no query coverage is shown
