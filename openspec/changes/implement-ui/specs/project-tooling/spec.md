## MODIFIED Requirements

### Requirement: Production build command
The project SHALL provide a `pnpm build` command that produces a production server build and fails if the code has type or build errors, and a `pnpm start` command that serves that build on the port given by the `PORT` environment variable (default 3000). The build MUST NOT require database credentials or reach the database.

#### Scenario: Successful build
- **WHEN** `pnpm build` runs without any Supabase or auth environment variables set
- **THEN** it exits 0 and produces a build that `pnpm start` can serve

#### Scenario: Start on the hosting port
- **WHEN** `pnpm start` runs with `PORT=10000` after a successful build
- **THEN** the app accepts HTTP requests on port 10000

## ADDED Requirements

### Requirement: Database type generation command
The project SHALL provide a package script that regenerates the committed TypeScript database types from the live Supabase schema. The generated file MUST be committed so builds never need database access.

#### Scenario: Regenerate types
- **WHEN** a developer with Supabase CLI access runs the type-generation script
- **THEN** the committed database types file is rewritten from the current schema and `pnpm typecheck` still passes

### Requirement: Development seed command
The project SHALL provide a package script that inserts a set of clearly marked sample jobs, together with their job sources, into the configured database for local development. It MUST NOT alter the schema. It MUST be safe to run more than once, without creating duplicates. It MUST refuse to run when `NODE_ENV` is `production`.

#### Scenario: Seeding an empty database
- **WHEN** the seed script runs against a database with no jobs
- **THEN** sample jobs exist afterwards, spread across role tracks, location buckets, work modes, fit scores and salary states, and some of them were first seen within the last 24 hours

#### Scenario: Re-running the seed
- **WHEN** the seed script runs a second time
- **THEN** the number of sample jobs is unchanged

#### Scenario: Production guard
- **WHEN** the seed script runs with `NODE_ENV=production`
- **THEN** it exits non-zero without writing anything

### Requirement: Unit test command
The project SHALL provide a `pnpm test` command that runs the unit tests once, without watch mode, and exits non-zero on any failure. The aggregate `pnpm check` MUST include it.

#### Scenario: Failing test fails the check
- **WHEN** a unit test fails and `pnpm check` runs
- **THEN** the command exits non-zero
