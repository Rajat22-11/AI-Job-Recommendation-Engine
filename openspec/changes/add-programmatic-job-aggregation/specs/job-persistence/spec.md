# Spec Delta

## Purpose

Normalises raw listings and stores them in the existing Supabase database exactly once each, so the read-only interface shows clean, de-duplicated jobs together with where each came from.

## ADDED Requirements

### Requirement: Normalise listings before storing
The system SHALL normalise each raw listing into the existing `jobs` fields, including location bucket, work mode, employment type, experience range, salary figures in lakhs per annum when stated, skills and posting date.

#### Scenario: Salary text converted
- **WHEN** a listing states a salary in lakhs per annum
- **THEN** the stored job carries the minimum and maximum in lakhs

#### Scenario: Unknown value
- **WHEN** a field cannot be determined
- **THEN** it is stored empty and the job is still stored

### Requirement: Reject invalid listings
The system SHALL discard a listing that lacks a title, a company, or an apply URL, and SHALL count and log each discard with its reason.

#### Scenario: No apply URL
- **WHEN** a listing has no apply URL
- **THEN** it is not stored and the discard is counted against its source

### Requirement: Deduplicate by company, title and location
The system SHALL identify a job by a key built from its normalised company, title and location, and SHALL store each key at most once.

#### Scenario: Same job from two sources
- **WHEN** the same company, title and location arrive from two sources
- **THEN** one job is stored and both sources are linked to it

#### Scenario: Same job on a later run
- **WHEN** a job already stored is fetched again
- **THEN** no new job is created and its last-seen time is updated

### Requirement: Record every source of a job
The system SHALL store a source link for each source a job was seen from, including the source identifier and the URL on that source.

#### Scenario: Source link stored
- **WHEN** a job is stored or seen again
- **THEN** a link to the source and its URL exists for that job

### Requirement: Writes are safe to repeat
The system SHALL make storing a batch repeatable so that rerunning after a partial failure creates no duplicates.

#### Scenario: Run restarted after failure
- **WHEN** a run is repeated after failing midway
- **THEN** jobs already stored are not duplicated and the remaining jobs are stored

### Requirement: Retire stale jobs
The system SHALL mark a job inactive when it has not been seen for a configurable number of days or is older than the configured maximum job age.

#### Scenario: Old job retired
- **WHEN** a job exceeds the maximum age in `search_config`
- **THEN** it is marked inactive and remains in the database

### Requirement: Exclude configured companies and out-of-scope jobs
The system SHALL NOT store a job from a company listed in the excluded companies of `search_config`.

#### Scenario: Excluded company
- **WHEN** a listing's company is in the excluded list
- **THEN** it is discarded and counted

### Requirement: Database changes need explicit approval
The system MUST NOT change the live database schema without the owner's approval, and any schema change MUST be provided as a reviewable migration.

#### Scenario: Schema addition proposed
- **WHEN** the pipeline needs a new table or default
- **THEN** the change is delivered as a migration file and is applied only after the owner approves
