# source-registry Specification

## Purpose

Gives developers one human-readable file that declares every website and every LinkedIn profile the pipeline crawls, so what runs is visible at a glance and can be changed without touching code.

## Requirements

### Requirement: Single registry file lists all crawl targets
The system SHALL read all job websites and all LinkedIn profiles to crawl from one registry file in a human-readable text format kept in the repository.

#### Scenario: Developer reviews active targets
- **WHEN** a developer opens the registry file
- **THEN** every website and every LinkedIn profile the pipeline can crawl is listed there, each with its enabled or disabled state

#### Scenario: Target absent from the file is never crawled
- **WHEN** a website or LinkedIn profile is not listed in the registry file
- **THEN** the pipeline does not fetch from it

### Requirement: Each target is described by a stable identifier and fetch settings
The system SHALL give every registry entry a unique identifier, a display name, a fetch method, an enabled flag, and the settings that method needs.

#### Scenario: Entry carries its own settings
- **WHEN** a source entry is read
- **THEN** its identifier, name, fetch method, enabled flag and method-specific settings are available without consulting any other file

#### Scenario: Duplicate identifiers are rejected
- **WHEN** two entries share the same identifier
- **THEN** loading fails with an error naming the duplicate identifier

### Requirement: Disabled targets are skipped but remain documented
The database flag `enabled` for a source decides whether it runs. The registry's `enabled` flag only sets the starting value for a source not yet in the database; after that the UI owns the flag. The system MUST skip any source whose effective enabled flag is false while keeping its entry in the registry.

#### Scenario: Disabled source is not fetched
- **WHEN** a source is disabled in the database
- **THEN** the run does not fetch from it and records no failure for it

#### Scenario: UI toggle overrides the registry file
- **WHEN** the registry file says `enabled: true` but the source is disabled in the database
- **THEN** the run does not fetch from it

#### Scenario: Registry sets the starting value for a new source
- **WHEN** a registry entry is not yet in the database
- **THEN** the entry is created with the registry's enabled flag

#### Scenario: Re-enabling needs no code change
- **WHEN** a source is enabled in the database
- **THEN** the next run fetches from it without any code change

### Requirement: Registry is validated before any run starts
The system SHALL validate the registry at load time and stop the run before fetching anything if it is malformed.

#### Scenario: Missing required field
- **WHEN** an entry lacks its identifier, fetch method or enabled flag
- **THEN** loading fails with an error that names the entry and the missing field

#### Scenario: Unknown fetch method
- **WHEN** an entry names a fetch method the system does not support
- **THEN** loading fails with an error that names the entry and the unsupported method

### Requirement: Registry holds no secrets
The registry file MUST NOT contain tokens, passwords or other credentials.

#### Scenario: Credentials referenced by service name only
- **WHEN** an entry needs a credentialed service
- **THEN** it names the service only, and the credentials are resolved elsewhere

### Requirement: Search criteria stay in the existing database configuration
The system SHALL keep search criteria such as keywords, locations, experience limits and excluded companies in the existing `search_config` table and SHALL NOT duplicate them in the registry.

#### Scenario: Criteria edited in one place
- **WHEN** a keyword is added to `search_config`
- **THEN** the next run uses it without any change to the registry file

### Requirement: Sources not fetched are recorded as skipped
The system SHALL record a `skipped` status with a reason for every source that is enabled in the database but has no fetcher. It SHALL use the reason from the `not_fetched` section of the registry, or, for a source listed in neither section, a reason stating the source is not in the registry.

#### Scenario: Listed in not_fetched
- **WHEN** an enabled source is listed under `not_fetched` with a reason
- **THEN** each run records it as skipped with that reason and fetches nothing from it

#### Scenario: Absent from the registry
- **WHEN** an enabled source appears in neither `sources` nor `not_fetched`
- **THEN** each run records it as skipped, stating that it is not in the source registry

#### Scenario: Identifier listed in both sections
- **WHEN** a source identifier appears in both `sources` and `not_fetched`
- **THEN** loading the registry fails with an error naming the identifier
