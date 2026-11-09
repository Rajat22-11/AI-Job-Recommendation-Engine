# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
