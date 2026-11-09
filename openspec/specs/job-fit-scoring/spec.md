# job-fit-scoring Specification

## Purpose

Rates how well each new job fits the owner's search criteria and explains the rating, using fixed rules by default and an optional language model only when explicitly enabled.

## Requirements

### Requirement: Score every new job from 1 to 5 with a reason
The system SHALL assign each newly stored job a whole-number fit score from 1 to 5 and a short plain-text reason.

#### Scenario: Job scored
- **WHEN** a new job is stored
- **THEN** it has a fit score between 1 and 5 and a non-empty reason

### Requirement: Rules-based scoring is the default
The system SHALL score using fixed rules over the criteria in `search_config` and SHALL NOT call a language model unless the optional scorer is enabled in configuration.

#### Scenario: Optional scorer off
- **WHEN** the optional scorer is not enabled
- **THEN** scoring completes without any language-model call

#### Scenario: Same input, same score
- **WHEN** the same job is scored twice with unchanged configuration
- **THEN** both scores and reasons are identical

### Requirement: Score against the search criteria
The system SHALL take into account keyword match on the job's title and skills, location match, required experience against the maximum allowed, and stated salary against the minimum, and SHALL lower the score when a criterion is not met. Keyword match SHALL use the word-ratio rule from job-source-fetching and SHALL NOT use the description text.

#### Scenario: Experience above the limit
- **WHEN** a job requires more experience than `max_required_yoe`
- **THEN** its score is lowered and the reason states the experience mismatch

#### Scenario: Salary not disclosed
- **WHEN** a job states no salary
- **THEN** the salary criterion is neither rewarded nor penalised and the reason says salary is undisclosed

#### Scenario: Keyword only in the description
- **WHEN** a search keyword appears only in the job description
- **THEN** the keyword criterion is not met and the reason says no keyword matched

### Requirement: Flag internships and batch-restricted roles
The system SHALL flag a job as an internship or batch-restricted when its title, employment type or text says so, and SHALL lower its score and state this in the reason.

#### Scenario: Intern role detected
- **WHEN** a job is described as an intern role for a graduating batch
- **THEN** the job is flagged and the reason says it is an internship

### Requirement: Optional language-model scoring is configurable
When the optional scorer is enabled, the system SHALL send only the minimal job text and a short criteria summary, SHALL use the credential pool for its tokens, SHALL keep its calls at least the configured minimum gap apart, SHALL take its wording from the prompt file in configuration while keeping the JSON answer format fixed, and SHALL fall back to rules-based scoring if the service is unavailable or no token is set. The shipped configuration enables the scorer for borderline jobs.

#### Scenario: Scorer enabled and available
- **WHEN** the optional scorer is enabled and a token works
- **THEN** the score and reason come from the language model for jobs the rules mark as borderline

#### Scenario: Scorer unavailable
- **WHEN** every token is exhausted or the call fails
- **THEN** the job is scored by the rules and the run is not failed

#### Scenario: Enabled without a key
- **WHEN** the scorer is enabled but no token is configured
- **THEN** the system logs a warning and scores every job by the rules

#### Scenario: Calls spaced out
- **WHEN** several borderline jobs are reviewed in one run
- **THEN** consecutive calls are at least the configured minimum gap apart

### Requirement: Scoring never blocks storing a job
The system SHALL store a job even if scoring errors, using a neutral score and a reason that states scoring failed.

#### Scenario: Scoring error
- **WHEN** scoring raises an error for one job
- **THEN** the job is still stored and the error is logged

### Requirement: Seniority in the title without stated experience
The system SHALL lower the score of a job whose title contains a seniority word, such as senior, lead, principal, staff, architect, manager, head or director, when the listing states no years of experience, and SHALL state this in the reason.

#### Scenario: Senior title without years stated
- **WHEN** a job titled "Senior Backend Engineer" states no years of experience
- **THEN** its score is lowered and the reason says the seniority word was found and the years are unknown

#### Scenario: Years stated
- **WHEN** a job with a senior title states an experience range
- **THEN** the seniority word does not lower the score; the stated range is used instead
