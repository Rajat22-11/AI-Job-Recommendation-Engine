# Spec Delta

## Purpose

Rates how well each new job fits the owner's search criteria and explains the rating, using fixed rules by default and an optional language model only when explicitly enabled.

## ADDED Requirements

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
The system SHALL take into account keyword and skill match, location match, required experience against the maximum allowed, and stated salary against the minimum, and SHALL lower the score when a criterion is not met.

#### Scenario: Experience above the limit
- **WHEN** a job requires more experience than `max_required_yoe`
- **THEN** its score is lowered and the reason states the experience mismatch

#### Scenario: Salary not disclosed
- **WHEN** a job states no salary
- **THEN** the salary criterion is neither rewarded nor penalised and the reason says salary is undisclosed

### Requirement: Flag internships and batch-restricted roles
The system SHALL flag a job as an internship or batch-restricted when its title, employment type or text says so, and SHALL lower its score and state this in the reason.

#### Scenario: Intern role detected
- **WHEN** a job is described as an intern role for a graduating batch
- **THEN** the job is flagged and the reason says it is an internship

### Requirement: Optional language-model scoring is configurable
When the optional scorer is enabled, the system SHALL send only the minimal job text and a short criteria summary, SHALL use the credential pool for its tokens, and SHALL fall back to rules-based scoring if the service is unavailable.

#### Scenario: Scorer enabled and available
- **WHEN** the optional scorer is enabled and a token works
- **THEN** the score and reason come from the language model for jobs the rules mark as borderline

#### Scenario: Scorer unavailable
- **WHEN** every token is exhausted or the call fails
- **THEN** the job is scored by the rules and the run is not failed

### Requirement: Scoring never blocks storing a job
The system SHALL store a job even if scoring errors, using a neutral score and a reason that states scoring failed.

#### Scenario: Scoring error
- **WHEN** scoring raises an error for one job
- **THEN** the job is still stored and the error is logged
