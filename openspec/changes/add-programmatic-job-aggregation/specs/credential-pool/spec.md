# Spec Delta

## Purpose

Lets one service be backed by several tokens from different accounts and moves to the next token automatically when one hits a rate limit or quota, so a run is not lost to a single exhausted token.

## ADDED Requirements

### Requirement: Multiple tokens per service
The system SHALL accept an ordered list of one or more tokens for each named service, including at least the LinkedIn post fetching service and the optional language-model service.

#### Scenario: Several tokens configured
- **WHEN** three tokens are configured for one service
- **THEN** the system holds all three in the order given and uses the first available one

#### Scenario: Single token configured
- **WHEN** only one token is configured for a service
- **THEN** the service works with that token and behaves as a pool of one

### Requirement: Tokens come from configuration outside the repository
The system MUST read tokens from the runtime environment or secret store and MUST NOT require them in any file committed to the repository.

#### Scenario: Tokens provided as secrets
- **WHEN** a run starts on the hosting service, with tokens supplied through its environment
- **THEN** tokens are read from secrets supplied to the run

#### Scenario: Token missing for a needed service
- **WHEN** a service in use has no configured token
- **THEN** that service's sources fail with a clear error naming the service, and other services continue

### Requirement: Rotate to the next token on rate limit or quota failure
The system SHALL retry a failed call with the next token when the service reports a rate limit, quota exhaustion, or a rejected token.

#### Scenario: First token exhausted
- **WHEN** a call fails because the first token's quota is used up
- **THEN** the call is retried with the second token and the first is marked unavailable

#### Scenario: Unrelated failure does not rotate
- **WHEN** a call fails for a reason unrelated to tokens, such as a malformed request
- **THEN** the system does not switch tokens

### Requirement: Unavailable tokens are not reused within a run
The system SHALL NOT use a token again in the same run once it has been marked unavailable.

#### Scenario: Later call skips exhausted token
- **WHEN** a second source needs the same service after the first token was marked unavailable
- **THEN** it starts with the next available token

### Requirement: Failure when every token is exhausted
The system SHALL fail the affected sources with an error stating that all tokens for the service are unavailable, and SHALL continue with unaffected sources.

#### Scenario: All tokens exhausted
- **WHEN** every token for a service is unavailable
- **THEN** the sources needing that service are recorded as failed with that reason and the run continues with other sources

### Requirement: Tokens never appear in output
The system MUST NOT write token values to logs, notifications, database rows or error messages.

#### Scenario: Failure message is redacted
- **WHEN** a call fails and the failure is logged
- **THEN** the log identifies the token only by its position in the list, never by its value
