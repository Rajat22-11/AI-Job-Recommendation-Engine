# Spec Delta

## Purpose

Retrieves raw job listings from each configured source type in a read-only, polite and failure-tolerant way and hands them on in one common shape, so downstream steps never depend on any site's format.

## ADDED Requirements

### Requirement: Supported source types
The system SHALL fetch jobs from open API or feed sources, from job boards through the JobSpy library (Indeed, Naukri, Glassdoor), and from company applicant-tracking boards (Greenhouse, Lever, Ashby), each selected by the entry's fetch method in the registry.

#### Scenario: Entry uses its declared method
- **WHEN** a registry entry names a fetch method
- **THEN** jobs are fetched using that method and no other

### Requirement: Common raw listing shape
The system SHALL return every fetched listing in one common shape carrying at least title, company, location, apply URL, source identifier and, when the source provides them, posting date, description, salary text and experience range.

#### Scenario: Different sources, same shape
- **WHEN** a listing is fetched from an API source and another from a job board
- **THEN** both are returned with the same set of fields

#### Scenario: Missing optional field
- **WHEN** a source does not provide a posting date
- **THEN** the field is returned empty and the listing is not discarded for that reason

### Requirement: Read-only access without credentials or challenges
The system MUST only read publicly available pages and endpoints, MUST NOT enter site credentials, create accounts, submit forms or click apply, and MUST NOT attempt to solve CAPTCHAs or other human-verification challenges.

#### Scenario: Login wall encountered
- **WHEN** a source responds with a login or verification page
- **THEN** the source is recorded as blocked for that run and the system makes no attempt to get past it

### Requirement: Respect each source's published usage terms
The system SHALL stay within each source's published rate limits and attribution requirements and SHALL keep fetched listings private to the owner's own database and interface.

#### Scenario: Source with a call limit
- **WHEN** a source documents a maximum number of calls per day
- **THEN** the system calls it no more often than that limit, however many runs occur

#### Scenario: Attribution retained
- **WHEN** a listing comes from a source that requires credit
- **THEN** the original listing URL and source name are kept with the stored job

### Requirement: Failure of one source does not stop the others
The system SHALL catch each source's failure, record its reason, and continue with the remaining sources.

#### Scenario: One source times out
- **WHEN** a source times out or returns an error
- **THEN** the run records that source as failed with the reason and fetches the remaining sources

### Requirement: Bounded retries and request pacing
The system SHALL pace requests to each source and SHALL retry transient failures a limited, configurable number of times before recording failure.

#### Scenario: Transient error recovers
- **WHEN** a request fails once with a temporary error and succeeds on retry
- **THEN** the listings are returned and the source is recorded as successful

#### Scenario: Retries exhausted
- **WHEN** every allowed retry fails
- **THEN** the source is recorded as failed and no further requests are made to it in that run

### Requirement: Search terms come from the database configuration
The system SHALL build searches from the keywords and locations in `search_config` and SHALL NOT hard-code search terms in code.

#### Scenario: Keywords changed
- **WHEN** `search_config` lists a new keyword
- **THEN** sources that accept keyword searches use it in the next run

### Requirement: Blocked boards can be fetched from another environment
The system SHALL allow the same fetch step for IP-sensitive boards to run from a different machine than the hosted cloud run, writing to the same database.

#### Scenario: Board blocked from cloud
- **WHEN** a job board refuses requests from the cloud environment
- **THEN** the same sources can be fetched by a run on the owner's own machine and the results are stored without duplicates
