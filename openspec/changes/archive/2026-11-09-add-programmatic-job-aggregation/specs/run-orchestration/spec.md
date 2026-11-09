# Spec Delta

## Purpose

Runs the whole pipeline once a day without anyone watching, records what happened per source, raises an alert when something silently stops working, and tells the owner the result.

## ADDED Requirements

### Requirement: One run covers every enabled source
The system SHALL, on each run, process every enabled source in the registry and record the run in the database.

#### Scenario: Full run
- **WHEN** a run starts
- **THEN** every enabled source is attempted and a run record exists with its start and finish time and overall status

### Requirement: Per-source status is recorded
The system SHALL record for each source in each run its status (succeeded, partial, failed, blocked or skipped), the number found, the number new, and a message.

#### Scenario: Source succeeds
- **WHEN** a source returns listings
- **THEN** its record shows succeeded with the counts of found and new jobs

#### Scenario: Source skipped
- **WHEN** a source is not attempted
- **THEN** its record shows skipped with the reason

### Requirement: Detect sources that silently return nothing
The system SHALL raise a health alert when a source returns zero listings, or far fewer than its recent average, for a configurable number of consecutive runs.

#### Scenario: Source drops to zero
- **WHEN** a source that normally returns jobs returns none for the configured number of runs
- **THEN** the run's notification names that source as unhealthy

### Requirement: Detect a missed run
The system SHALL alert the owner when no run has been recorded within the configured number of hours.

#### Scenario: No run in 24 hours
- **WHEN** more than the configured hours pass without a recorded run
- **THEN** an alert is sent through the notification channel

### Requirement: Notify the owner of each run
The system SHALL send one notification per run through a configurable channel summarising new jobs, the best matches, and any source problems.

#### Scenario: Run with new jobs
- **WHEN** a run stores new jobs
- **THEN** one notification lists the count, the top matches by score, and any failed or unhealthy sources

#### Scenario: Notification channel unreachable
- **WHEN** the notification cannot be sent
- **THEN** the run still completes and the failure is recorded in the run summary

### Requirement: Hosted as a service started by an external daily trigger
The system SHALL run as a web service on a free host that does not use its own scheduler, and SHALL start the daily run when an external scheduled trigger calls an authenticated start endpoint, once a day at a configurable off-peak time. The run SHALL also be startable manually through the same endpoint.

#### Scenario: Scheduled start
- **WHEN** the configured time arrives and the trigger calls the start endpoint with a valid secret
- **THEN** a run starts without manual action

#### Scenario: Manual start
- **WHEN** the owner calls the start endpoint by hand with a valid secret
- **THEN** it behaves exactly as a scheduled run

### Requirement: Start returns at once and the run continues in the background
The system SHALL answer a start request immediately with a run identifier, SHALL execute the pipeline in the background independent of the request connection, and SHALL expose a status endpoint that reports the run's state and summary.

#### Scenario: Start accepted
- **WHEN** a valid start request arrives and no run is active
- **THEN** the response comes back quickly with a run identifier and the run proceeds in the background

#### Scenario: Status checked
- **WHEN** the trigger or owner asks for the status of a run identifier
- **THEN** the response states whether the run is running, finished, failed or interrupted, with its summary once finished

#### Scenario: Service restarted mid-run
- **WHEN** the service restarts while a run is recorded as running
- **THEN** the run is reported as interrupted and not as running

### Requirement: Overlapping runs are refused
The system SHALL allow at most one active run and SHALL answer a start request made while a run is active with that run's identifier, without starting another run.

#### Scenario: Second trigger during a run
- **WHEN** a start request arrives while a run is active
- **THEN** no new run starts and the response names the active run

#### Scenario: Repeated trigger after completion the same day
- **WHEN** the trigger is repeated after the day's run has finished
- **THEN** the behaviour follows configuration: either a new run starts, or the response names the finished run and nothing starts

### Requirement: Endpoints are protected by a rotatable shared secret
The system SHALL reject any start, status or health-check request that lacks a valid shared secret, SHALL accept any one of several configured secrets so that a secret can be rotated without downtime, SHALL compare secrets without leaking them through timing, and SHALL never write a secret to logs or responses. A liveness endpoint returning no data MAY be unauthenticated.

#### Scenario: Missing or wrong secret
- **WHEN** a request carries no secret or an unknown secret
- **THEN** it is rejected and no run starts

#### Scenario: Rotation
- **WHEN** two secrets are configured and a request uses either one
- **THEN** the request is accepted

### Requirement: The trigger tolerates a sleeping service
The system SHALL let the trigger retry the start request with backoff for a configurable time to allow a cold-starting service to wake, SHALL poll the status endpoint until the run finishes or a configured limit passes, and SHALL fail visibly when the service cannot be reached or the run does not finish.

#### Scenario: Service asleep
- **WHEN** the first start request times out because the service is waking
- **THEN** the trigger retries until the service answers or the configured wait ends

#### Scenario: Service unreachable
- **WHEN** the service does not answer within the configured wait
- **THEN** the trigger fails visibly so the owner is alerted

#### Scenario: Run does not finish
- **WHEN** the run is still running after the configured limit
- **THEN** the trigger fails visibly and names the run identifier

### Requirement: The pipeline stays runnable as a plain command
The system SHALL expose the same pipeline through a command-line entry point, so that it can run from the owner's machine or, as a documented fallback, inside the scheduler's own job.

#### Scenario: Run from the command line
- **WHEN** the owner runs the entry point directly
- **THEN** the same pipeline executes against the same database and records its run

### Requirement: Safe to run from more than one place
The system SHALL allow the run, or a chosen subset of sources, to execute from another machine against the same database without creating duplicates.

#### Scenario: Subset run from owner's machine
- **WHEN** the owner runs only the job-board sources locally
- **THEN** the results merge with the cloud run's results and no job is duplicated

### Requirement: Configuration of behaviour lives outside code
The system SHALL read run limits, retry counts, health thresholds, notification channel, trigger wait and polling limits, and the repeat-trigger behaviour from configuration rather than from code.

#### Scenario: Threshold changed
- **WHEN** the owner changes the health threshold in configuration
- **THEN** the next run uses it without a code change

### Requirement: Existing routine retired only on approval
The system MUST NOT disable the existing Claude routine until the owner confirms the pipeline covers its sources.

#### Scenario: Parity reached
- **WHEN** the pipeline has run successfully alongside the Claude routine
- **THEN** the routine is disabled only after the owner explicitly approves
