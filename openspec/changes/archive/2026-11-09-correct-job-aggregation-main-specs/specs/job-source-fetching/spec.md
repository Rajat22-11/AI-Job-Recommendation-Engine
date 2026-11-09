# Spec Delta

## MODIFIED Requirements

### Requirement: Supported source types
The system SHALL fetch jobs from open API, feed and public-page sources, from job boards, and from company applicant-tracking boards (Greenhouse, Lever, Ashby), each selected by the entry's fetch method in the registry. Job boards are Indeed through the JobSpy library, Naukri through an Apify actor, and Glassdoor through the JobSpy library, which is currently blocked for the owner's sessions.

#### Scenario: Entry uses its declared method
- **WHEN** a registry entry names a fetch method
- **THEN** jobs are fetched using that method and no other

#### Scenario: Naukri read through Apify
- **WHEN** the Naukri entry is fetched
- **THEN** the request goes to the Apify actor named in the registry, not to Naukri directly

## ADDED Requirements

### Requirement: Keyword matching for broad listings
The system SHALL keep a listing from a broad source only when a search keyword matches its title or skills. A keyword matches when the share of its significant words, meaning words that are not generic such as "developer" or "engineer", found in that text reaches the configured `prefilter_min_ratio`. Description text alone SHALL NOT count as a match. The We Work Remotely feed matches on the title only, because each of its items carries a category label.

#### Scenario: Significant words found in the title
- **WHEN** a keyword's significant words reach the configured ratio in the listing's title or skills
- **THEN** the listing is kept

#### Scenario: Keyword only in the description
- **WHEN** a keyword's words appear only in the listing's description
- **THEN** the listing is dropped

### Requirement: Naukri searches are capped
The system SHALL read Naukri through an Apify actor with at most the configured number of searches per run, asking only for the newest jobs and only for jobs within the configured freshness window, and SHALL keep each job's Naukri page as its source link.

#### Scenario: Search budget reached
- **WHEN** the configured number of searches for a run has been made
- **THEN** no further Naukri searches are made in that run

### Requirement: Public feeds and pages are filtered to India
The system SHALL keep Working Nomads, We Work Remotely and Arc listings only when their location is open to India or to anyone worldwide, and SHALL keep the original source link for each listing.

#### Scenario: Listing restricted to another country
- **WHEN** a listing is restricted to a country other than India
- **THEN** it is dropped

#### Scenario: Original link kept
- **WHEN** a listing from one of these sources is stored
- **THEN** its original page on that source is recorded as the source link
