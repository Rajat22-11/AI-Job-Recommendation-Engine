# project-tooling Specification

## Purpose
Defines how developers and the build environment install, check, format, and build the project, so every machine and the hosting build produce the same result.
## Requirements
### Requirement: Single package manager
The project SHALL use pnpm as its only package manager. The repository MUST declare the exact pnpm version in its package manifest, MUST contain a pnpm lockfile, and MUST NOT contain lockfiles for any other package manager.

#### Scenario: Clean install from lockfile
- **WHEN** a developer or build environment runs a frozen-lockfile pnpm install on a fresh checkout
- **THEN** the install succeeds without modifying the lockfile

#### Scenario: Foreign lockfile absent
- **WHEN** the repository root is inspected
- **THEN** only `pnpm-lock.yaml` is present and no `package-lock.json`, `yarn.lock` or `bun.lock*` exists

### Requirement: Pinned Node.js runtime
The project SHALL declare Node.js 24 as its supported runtime in both the package manifest and a version file that hosting providers read.

#### Scenario: Runtime declaration
- **WHEN** the package manifest and `.node-version` are read
- **THEN** both specify Node.js major version 24

### Requirement: Quality check commands
The project SHALL provide package scripts for linting, type-checking, format checking, formatting, and an aggregate check. Each check command MUST exit with a non-zero status when it finds a violation and with zero when the codebase is clean.

#### Scenario: Clean codebase passes
- **WHEN** `pnpm check` runs on the freshly set-up project
- **THEN** linting, type-checking and format checking all pass and the command exits 0

#### Scenario: Type error fails the check
- **WHEN** a source file contains a TypeScript type error and `pnpm typecheck` runs
- **THEN** the command exits non-zero and reports the error

#### Scenario: Unformatted file fails the check
- **WHEN** a source file is not formatted according to project rules and `pnpm format:check` runs
- **THEN** the command exits non-zero and names the file

### Requirement: Platform-independent formatting
Text files SHALL be stored with LF line endings regardless of the developer's operating system, so formatting checks produce the same result on Windows and on the Linux build environment.

#### Scenario: Windows checkout
- **WHEN** the repository is checked out on Windows and `pnpm format:check` runs
- **THEN** no file is reported as unformatted because of line endings

### Requirement: Production build command
The project SHALL provide a `pnpm build` command that produces the deployable site and fails if the code has type or build errors.

#### Scenario: Successful build
- **WHEN** `pnpm build` runs with the required environment variables set
- **THEN** it exits 0 and writes the deployable output to the `out/` directory

