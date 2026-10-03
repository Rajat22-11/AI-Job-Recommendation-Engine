## Purpose

Lets the user change what the scraper searches for and which sites it uses, by editing the single `search_config` row and the `sources` table from the app instead of the database console.

## ADDED Requirements

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
The settings page SHALL let the user add a source with:
- id: required; 2 to 40 characters of lowercase letters, digits, `-` or `_`; unique
- name: required
- base URL: required, an absolute http(s) URL
- access method: `connector`, `public_scrape` or `browser_session`
- search URL template: optional
- requires login and enabled: both checkboxes, enabled on by default
- notes: optional

A duplicate id MUST be rejected with "A source with this id already exists".

#### Scenario: New source
- **WHEN** the user adds id `instahyre`, name "Instahyre", base URL `https://www.instahyre.com`, access method `public_scrape`
- **THEN** the source exists, is enabled, and is listed on `/sources`

#### Scenario: Duplicate id
- **WHEN** the user adds a source whose id already exists
- **THEN** nothing is saved and the id field shows the duplicate error

### Requirement: Edit a source
The settings page SHALL let the user edit every field of an existing source except its id, which is shown read-only because job links and run history refer to it. Sources MUST NOT be deletable from the app. Disabling a source is the supported way to retire it.

#### Scenario: Rename a source
- **WHEN** the user changes source `naukri`'s name to "Naukri.com"
- **THEN** feed badges and the sources page show "Naukri.com", and the id is still `naukri`

### Requirement: Search URL template help and validation
The search URL template field SHALL explain the placeholders `{query}` (URL-encoded keyword), `{query_slug}` (keyword lowercased with spaces turned into hyphens) and `{location}` (URL-encoded location). It MUST show an example expansion of the saved template, built from the first configured keyword and location. A template MUST be an absolute http(s) URL after its placeholders are expanded. A template containing any other `{…}` placeholder MUST be rejected, with a message naming the unknown placeholder.

#### Scenario: Example expansion
- **WHEN** the template is `https://example.com/jobs/{query_slug}-jobs-in-{location}` and the first keyword and location are "Java Developer" and "Pune"
- **THEN** the example shown is `https://example.com/jobs/java-developer-jobs-in-Pune`

#### Scenario: Unknown placeholder
- **WHEN** the user saves a template containing `{city}`
- **THEN** nothing is saved and the error names `{city}`
