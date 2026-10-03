## MODIFIED Requirements

### Requirement: Job card contents
Each feed item SHALL show:
- title and company
- location text and a location-bucket badge
- work mode and role track
- salary in one of three states:
  - **not disclosed** (`salary_text` empty and both `salary_min_lpa` and `salary_max_lpa` empty): a neutral "Salary not disclosed" badge, and no salary text
  - **compared**: `salary_text` (or the LPA range when the text is empty), with a green "Meets min" badge when `salary_meets_min` is true
  - **not compared** (salary given, `salary_meets_min` empty): the salary as above, followed by a muted "not compared" note
- required experience from `min_yoe`/`max_yoe` ("1–3 yrs", "3+ yrs", "Up to 3 yrs"), omitted when both are empty
- fit score as "n/5" with `fit_reason`, or "Not scored" when the score is empty
- a relative posted date such as "Today", "1d ago", "3d ago", falling back to "Seen 3d ago" from `first_seen_at` when `posted_at` is empty
- a "NEW" badge when `first_seen_at` is less than 24 hours ago
- skill chips, at most 6 and then "+N"
- one badge per source in `links`
- the application status, unless it is `new`

The title MUST link to the job's detail page.

#### Scenario: Undisclosed salary
- **WHEN** a job has no `salary_text`, `salary_min_lpa` or `salary_max_lpa`
- **THEN** its card shows a "Salary not disclosed" badge and no "Meets min" badge

#### Scenario: Salary given but not compared
- **WHEN** a job has `salary_text` "Competitive + ESOPs" and `salary_meets_min` is empty
- **THEN** its card shows "Competitive + ESOPs" with a "not compared" note, and no "Salary not disclosed" badge

#### Scenario: Freshly scraped job
- **WHEN** a job's `first_seen_at` was 3 hours ago
- **THEN** its card shows a "NEW" badge

#### Scenario: Many skills
- **WHEN** a job lists 9 skills
- **THEN** the card shows the first 6 as chips followed by "+3"

### Requirement: Apply and source links
Each card SHALL have a primary "Apply" link to `apply_url` that opens in a new tab with `noopener` and `noreferrer`, plus a secondary link for every entry in `links`, labelled with the source name. Next to Apply, the card MUST show "Employer site" when `apply_url_kind` is `employer` and "Job board" when it is `board`, and nothing when it is empty. Opening Apply MUST NOT change the application status by itself.

#### Scenario: Apply opens externally
- **WHEN** the user taps "Apply" on a card
- **THEN** `apply_url` opens in a new tab, the feed stays open in the original tab, and the job's status is unchanged

#### Scenario: Employer link
- **WHEN** a job's `apply_url_kind` is `employer`
- **THEN** its card shows "Employer site" next to Apply

### Requirement: Quick triage actions
Each card SHALL offer "Save", "Applied" and "Skip" actions, and each MUST take effect in one tap.
- **Save** sets the status to `saved`. On a job that is already saved, the control reads "Saved" and tapping it removes the application record.
- **Applied** sets the status to `applied` and sets `applied_on` to today (IST), unless `applied_on` is already set.
- **Skip** sets the status to `skipped`. On a job that is already skipped, the control MUST instead read "Restore", and tapping it removes the application record, so the job's status is `new` again.

Other application fields (notes, resume version, referral contact) MUST be kept, except when Save or Restore removes the record. The card MUST show the new state immediately, without waiting for the server. Each action MUST then offer "Undo" for at least 5 seconds, which restores the exact previous application state, including having no record at all. If the server rejects an action, the card MUST revert and show an error.

#### Scenario: Mark applied
- **WHEN** the user taps "Applied" on a job whose status is `new`
- **THEN** an application record with status `applied` and today's IST date as `applied_on` exists, and the card shows "Applied"

#### Scenario: Skip leaves the default view
- **WHEN** the user taps "Skip" on a card in the default view
- **THEN** the card leaves the list and an "Undo" control is offered

#### Scenario: Undo a skip
- **WHEN** the user taps "Undo" after skipping a job that previously had no application record
- **THEN** the application record is removed again and the job reappears with status `new`

#### Scenario: Restore a skipped job
- **WHEN** the user taps "Restore" on a skipped job's card
- **THEN** its application record is removed, the card shows status `new`, and "Undo" puts the skipped record back with its notes

#### Scenario: Notes survive triage
- **WHEN** a saved job with notes is marked applied from the card
- **THEN** its notes, resume version and referral contact are unchanged

#### Scenario: Failed action
- **WHEN** a quick action fails on the server
- **THEN** the card returns to its previous state and an error message is shown

### Requirement: URL-driven filters
Filter and sort state SHALL live only in URL search parameters, so every view can be bookmarked and shared. These parameters are supported:
- `track`, `loc`, `mode`, `status`, `source`: each repeatable for multiple values. `status` accepts the values `new`, `saved`, `applied`, `interview`, `offer`, `rejected`, `skipped`, and the single value `all`.
- `fit`: minimum fit score, 0–5. `0` also includes unscored jobs.
- `salary`: `meets` (`salary_meets_min` true), `not_disclosed` (no salary text or figures), `unparsed` (salary given but `salary_meets_min` empty), `unknown` (`salary_meets_min` empty, which is both of the previous two), or `any`. The filter controls MUST offer `any`, `meets`, `not_disclosed` and `unparsed`. `unknown` MUST still be accepted from URLs and shown as its own active value.
- `posted`: 1, 3, 7 or 30, meaning posted within that many days. Jobs without a posted date are judged by `first_seen_at`.
- `seen`: `24h`, meaning first seen within the last 24 hours.
- `q`: text search.
- `sort`: `fit`, `newest` or `salary`.
- `page`.

Unknown or invalid values MUST be ignored. Changing any filter MUST reset to page 1. The filter controls MUST show the active values, and a "Reset filters" link MUST return to the default view.

#### Scenario: Bookmarked view
- **WHEN** the user opens `/?track=ml_ai&loc=pune&loc=remote_india&fit=4&sort=newest`
- **THEN** the feed shows only ML / AI jobs in Pune or Remote (India) with fit score ≥ 4, newest first, and the filter controls show exactly those choices

#### Scenario: Source filter
- **WHEN** the user filters by `source=naukri`
- **THEN** only jobs with at least one `links` entry from source `naukri` are shown

#### Scenario: Salary not disclosed
- **WHEN** `salary=not_disclosed` is applied
- **THEN** only jobs with no salary text and no salary figures are shown

#### Scenario: Salary not compared
- **WHEN** `salary=unparsed` is applied
- **THEN** only jobs that state a salary and whose `salary_meets_min` is empty are shown

#### Scenario: Salary unknown
- **WHEN** `salary=unknown` is applied
- **THEN** only jobs whose `salary_meets_min` is empty are shown, and the active filter reads "Salary unknown"

#### Scenario: Invalid parameter
- **WHEN** the URL contains `fit=9&sort=random`
- **THEN** the feed renders with the default fit filter and default sort, and no error

### Requirement: New today preset
The feed SHALL show a "New today (N)" control, where N is the number of active jobs first seen in the last 24 hours whose status is `new`, at any fit score and regardless of the feed's current filters. It MUST link to `/?seen=24h&status=new&fit=0`, which lists exactly those N jobs. There is no separate digest page.

#### Scenario: Opening new-today
- **WHEN** 7 active jobs were first seen in the last 24 hours, 2 of them already saved and 1 with fit score 1
- **THEN** the control reads "New today (5)", and following it lists those 5 jobs, including the one with fit score 1

#### Scenario: Current filters don't change the count
- **WHEN** the feed is filtered to `loc=pune` and 5 jobs are new today across all locations
- **THEN** the control still reads "New today (5)"

## ADDED Requirements

### Requirement: Hidden skipped jobs notice
When the status filter is not `all` and does not include `skipped`, the feed SHALL count the active jobs that match every other current filter and have status `skipped`. If that count N is above zero, the feed MUST show "1 skipped job hidden" or "N skipped jobs hidden", with a "Show" link to the same view with `skipped` added to the status filter. When N is zero, or skipped jobs are already included, nothing is shown.

#### Scenario: Skipped job hidden
- **WHEN** the default view is open and one active job with fit score 4 has status `skipped`
- **THEN** the feed shows "1 skipped job hidden" and "Show" leads to the default filters plus `status=skipped`

#### Scenario: Hidden by another filter too
- **WHEN** the feed is filtered to `loc=pune` and the only skipped job is in Mumbai
- **THEN** no hidden-skipped notice is shown

#### Scenario: Skipped included
- **WHEN** the status filter is `all`
- **THEN** no hidden-skipped notice is shown
