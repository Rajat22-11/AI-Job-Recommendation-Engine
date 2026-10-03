# search-settings Specification

## Purpose
Lets the user change what the scraper searches for and which sites it uses, by editing the single `search_config` row and the `sources` table from the app instead of the database console.

## Requirements

### Requirement: Edit search configuration
The page `/settings` SHALL show a form, pre-filled from the `search_config` row, for:
- keywords, locations and excluded companies: lists entered one per line, trimmed, with blank lines and duplicates (ignoring case) removed
- `min_salary_lpa`: a number from 0 to 1000
- `max_required_yoe`: a number from 0 to 50
- `max_job_age_days`: a whole number from 1 to 365

Keywords and locations MUST each have at least one entry. Saving MUST update the row, set `updated_at` to the current time, and show "Saved" together with the new last-updated time. Invalid input MUST be rejected with messages next to the fields, keeping what the user entered.

#### Scenario: Update keywords
- **WHEN** the user enters "java developer", a blank line, "Java Developer" and "ml engineer" as keywords and saves
- **THEN** `search_config.keywords` is `["java developer", "ml engineer"]` and `updated_at` is now

#### Scenario: Invalid number
- **WHEN** `max_job_age_days` is set to 0
- **THEN** nothing is saved and the field shows an error

#### Scenario: Empty keywords
- **WHEN** every keyword line is blank
- **THEN** nothing is saved and keywords shows "Add at least one keyword"

### Requirement: Add a source
The settings page SHALL let the user add a source with only:
- name: required, at most 100 characters
- base URL: required, an absolute http(s) URL
- requires login: checkbox, off by default
- notes: optional

The id MUST be derived from the name: lowercased, runs of characters other than letters and digits replaced by `-`, leading and trailing `-` removed, cut to 40 characters. When that leaves fewer than 2 characters, the id MUST be derived the same way from the base URL's host without a leading `www.`. When the id is already taken, `-2`, `-3` and so on up to `-9` MUST be appended until it is free. If none is free, nothing is saved and the name field says "Choose a different name".

A new source MUST be saved enabled, with access method `auto`, no search URL template, `template_status` `unverified` and no template origin. A base URL whose host matches an existing source's host MUST be rejected with "<name> already uses this site".

#### Scenario: New source
- **WHEN** the user adds name "Instahyre" and base URL `https://www.instahyre.com`
- **THEN** a source with id `instahyre`, access method `auto`, no template and `template_status` `unverified` exists, is enabled, and `/sources` shows it as waiting for its first run

#### Scenario: Duplicate id
- **WHEN** a source `instahyre` exists and the user adds name "Instahyre" with base URL `https://jobs.instahyre.in`
- **THEN** the new source's id is `instahyre-2`

#### Scenario: Name without letters or digits
- **WHEN** the user adds name "★" with base URL `https://www.foundit.in`
- **THEN** the new source's id is `foundit-in`

#### Scenario: Same site twice
- **WHEN** source "Himalayas" has base URL `https://himalayas.app` and the user adds base URL `https://himalayas.app/jobs`
- **THEN** nothing is saved and the base URL field shows "Himalayas already uses this site"

### Requirement: Edit a source
The settings page SHALL let the user edit an existing source's name, base URL, requires login, enabled and notes. Its id MUST be shown read-only because job links and run history refer to it. Sources MUST NOT be deletable from the app. Disabling a source is the supported way to retire it.

Saving these fields MUST NOT write `access_method`, `search_url_template` or any template field, so a template the trigger learned is never overwritten by a form loaded earlier.

An "Advanced override" section, collapsed by default, SHALL show the access method (any allowed value) and the search URL template. Only values the user changed in that section MUST be written:
- A changed access method is saved as given.
- A changed, non-empty template is saved with `template_origin` `manual`, `template_status` `unverified` and no `template_verified_at`.
- A template cleared to empty is saved as no template, with no template origin and `template_status` `unverified`, so the trigger learns one again.

#### Scenario: Rename a source
- **WHEN** the user changes source `naukri`'s name to "Naukri.com"
- **THEN** feed badges and the sources page show "Naukri.com", and the id is still `naukri`

#### Scenario: Learned template survives an edit
- **WHEN** the user opens a source's form, the trigger then learns a new template for it, and the user saves a changed name
- **THEN** the name is updated and the newly learned template is kept

#### Scenario: Manual override
- **WHEN** the user enters a template in "Advanced override" for a source with a learned template and saves
- **THEN** the source has that template, `template_origin` `manual` and `template_status` `unverified`

#### Scenario: Learned template with an unfamiliar placeholder
- **WHEN** the trigger learned a template containing `{page}` and the user edits only the notes
- **THEN** the notes are saved without a template error

### Requirement: Manual template validation
The Advanced override's template field SHALL explain the placeholders `{query}` (URL-encoded keyword), `{query_slug}` (keyword lowercased with spaces turned into hyphens) and `{location}` (URL-encoded location). It MUST show an example expansion of the source's current template, built from the first configured keyword and location. When the user changes the template, it MUST be an absolute http(s) URL after its placeholders are expanded. A changed template containing any other `{…}` placeholder MUST be rejected, with a message naming the unknown placeholder. An unchanged template MUST NOT be validated.

#### Scenario: Example expansion
- **WHEN** the template is `https://example.com/jobs/{query_slug}-jobs-in-{location}` and the first keyword and location are "Java Developer" and "Pune"
- **THEN** the example shown is `https://example.com/jobs/java-developer-jobs-in-Pune`

#### Scenario: Unknown placeholder
- **WHEN** the user changes the template to one containing `{city}` and saves
- **THEN** nothing is saved and the error names `{city}`

### Requirement: Settings last used by a run
Next to "Last updated", the search configuration form SHALL show "Last used by run <first 8 characters of run_id> at <time in IST>" for the most recently started run, found in `runs` or `source_runs`, linking to that run on `/runs`. When `search_config.updated_at` is later than that run's start, it MUST add "Changed after this run, applies from the next run." When there are no runs, it MUST show "Not used by any run yet". After a save, the note MUST reflect the new last-updated time without a reload.

#### Scenario: Settings unchanged since the last run
- **WHEN** the settings were last updated on 1 Oct and the latest run started on 3 Oct at 09:00 IST
- **THEN** the form shows "Last used by run 1a2b3c4d at" followed by 3 Oct 09:00 IST in the same format as "Last updated", and no "Changed after this run" note

#### Scenario: Settings changed after the last run
- **WHEN** the user saves the settings after the latest run started
- **THEN** the form shows "Changed after this run, applies from the next run."

#### Scenario: No runs
- **WHEN** neither `runs` nor `source_runs` has any rows
- **THEN** the form shows "Not used by any run yet"
