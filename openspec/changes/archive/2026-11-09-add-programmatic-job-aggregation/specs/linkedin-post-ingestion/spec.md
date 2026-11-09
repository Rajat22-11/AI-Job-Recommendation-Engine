# Spec Delta

## Purpose

Turns the latest hiring posts from configured LinkedIn influencer profiles into job listings by recognising hiring posts, reading their fields, and finding the employer's apply link, without logging in to LinkedIn.

## ADDED Requirements

### Requirement: Fetch latest posts for each configured profile
The system SHALL fetch only the most recent posts of each enabled LinkedIn profile in the registry, up to a configurable number per profile, without using a LinkedIn account or cookies.

#### Scenario: Latest posts requested
- **WHEN** a profile is enabled with a limit of three posts
- **THEN** at most the three newest posts of that profile are fetched

#### Scenario: Profile disabled
- **WHEN** a profile is marked disabled in the registry
- **THEN** no posts are fetched for it

### Requirement: Recognise hiring posts
The system SHALL treat a post as a hiring post only when it contains a hiring marker and an apply link, and SHALL ignore every other post.

#### Scenario: Hiring post accepted
- **WHEN** a post begins "Oracle IS HIRING!" and contains an "Apply link" line with a `lnkd.in` URL
- **THEN** the post is accepted for job extraction

#### Scenario: Non-hiring post ignored
- **WHEN** a post is a study cheatsheet with no apply link
- **THEN** the post produces no job and is not treated as an error

### Requirement: Extract labelled job fields
The system SHALL read the company, role, experience or batch, location, skills and stipend from the labelled lines of a hiring post.

#### Scenario: Fields present
- **WHEN** a post has Role, Experience, Location and Skills Required lines
- **THEN** the resulting job carries that role, experience range, location and skills

#### Scenario: Optional line absent
- **WHEN** a post has no stipend line
- **THEN** the job is created without a stipend and is not rejected

#### Scenario: Unparseable post
- **WHEN** a post has a hiring marker and link but no role can be read
- **THEN** the post is recorded as unparsed with its URL for review and no job is created

### Requirement: Resolve the apply link to the employer URL
The system SHALL resolve each short `lnkd.in` link to the employer's own apply URL using plain public requests, and SHALL store that destination as the job's apply URL.

#### Scenario: Short link resolved
- **WHEN** a post's apply link is a `lnkd.in` short link
- **THEN** the stored apply URL is the destination page named by that link, not the short link

#### Scenario: Link cannot be resolved
- **WHEN** the destination cannot be read
- **THEN** the job is stored with the original short link and flagged as unresolved

### Requirement: Never process the same post twice
The system SHALL record each processed post by its URL and SHALL skip any post already recorded.

#### Scenario: Post seen on a later run
- **WHEN** a post fetched today was processed yesterday
- **THEN** it is skipped and produces no duplicate job

### Requirement: Post source is traceable
The system SHALL keep the post URL and profile identifier with every job created from a post.

#### Scenario: Provenance recorded
- **WHEN** a job is created from a post
- **THEN** the stored job source records the profile and the post URL

### Requirement: Fetch cost stays within the free allowance
The system SHALL cap the posts requested per run so that expected monthly usage stays within the free allowance of the fetching service.

#### Scenario: Cap enforced
- **WHEN** configured profiles and post limits would exceed the configured per-run cap
- **THEN** the run fetches only up to the cap and records that it was limited
