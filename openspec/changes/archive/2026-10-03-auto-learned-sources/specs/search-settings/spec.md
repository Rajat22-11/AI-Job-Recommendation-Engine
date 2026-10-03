## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Search URL template help and validation
**Reason**: Templates are now learned by the trigger. Help and validation apply only to the manual override, so the requirement is restated as "Manual template validation".
**Migration**: See "Manual template validation".

## ADDED Requirements

### Requirement: Manual template validation
The Advanced override's template field SHALL explain the placeholders `{query}` (URL-encoded keyword), `{query_slug}` (keyword lowercased with spaces turned into hyphens) and `{location}` (URL-encoded location). It MUST show an example expansion of the source's current template, built from the first configured keyword and location. When the user changes the template, it MUST be an absolute http(s) URL after its placeholders are expanded. A changed template containing any other `{…}` placeholder MUST be rejected, with a message naming the unknown placeholder. An unchanged template MUST NOT be validated.

#### Scenario: Example expansion
- **WHEN** the template is `https://example.com/jobs/{query_slug}-jobs-in-{location}` and the first keyword and location are "Java Developer" and "Pune"
- **THEN** the example shown is `https://example.com/jobs/java-developer-jobs-in-Pune`

#### Scenario: Unknown placeholder
- **WHEN** the user changes the template to one containing `{city}` and saves
- **THEN** nothing is saved and the error names `{city}`
