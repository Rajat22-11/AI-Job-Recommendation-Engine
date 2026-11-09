# Spec Delta

## MODIFIED Requirements

### Requirement: Tokens come from configuration outside the repository
The system MUST read tokens from the runtime environment or secret store and MUST NOT require them in any file committed to the repository. For local runs it MAY read them from a git-ignored `.env.local` or `.env` file in the project folder; a variable already set in the real environment takes precedence over the file.

#### Scenario: Tokens provided as secrets
- **WHEN** a run starts on the hosting service, with tokens supplied through its environment
- **THEN** tokens are read from secrets supplied to the run

#### Scenario: Local run reads a git-ignored file
- **WHEN** a run starts locally and `.env.local` or `.env` names several tokens for one service, separated by commas
- **THEN** the same variable names and comma-separated lists are used as on the hosting service, and the tokens are tried in the order given

#### Scenario: Token missing for a needed service
- **WHEN** a service in use has no configured token
- **THEN** that service's sources fail with a clear error naming the service, and other services continue
