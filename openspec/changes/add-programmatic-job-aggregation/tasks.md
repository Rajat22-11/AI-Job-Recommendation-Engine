# Tasks

## 1. Project scaffolding

- [x] 1.1 Create the package layout from design.md D1 (`src/job_aggregator/` with `domain`, `registry`, `settings`, `credentials`, `fetching`, `linkedin`, `processing`, `scoring`, `persistence`, `health`, `notifications`, `orchestration`, `service`, plus `config/`, `tests/`, `migrations/`); verify every directory exists and the package imports without error
- [x] 1.2 Add project metadata and pinned dependencies (Python 3.11 or newer, YAML and data-validation libraries, a web framework and server for the trigger service, an HTTP client, the Supabase client, JobSpy, the Apify client, a test runner, a linter); verify a clean install in a fresh virtual environment succeeds
- [x] 1.3 Add lint and test commands and a `.gitignore` that excludes secrets, virtual environments and caches; verify the test command runs and reports zero tests collected without error
- [x] 1.4 Write the top-level README stating what the project does, the folder map, and how to run tests; verify the commands in it run as written

## 2. Domain models and errors

- [x] 2.1 Define the raw listing, normalised job, fetch result, source status and run summary models with the fields named in the job-source-fetching and job-persistence specs; verify unit tests build each model and reject missing required fields
- [x] 2.2 Define the error types (invalid registry, source blocked, source timeout, all tokens exhausted, listing rejected) with clear messages; verify a unit test checks each message names the entry or service involved

## 3. Source registry

- [x] 3.1 Write `config/sources.yaml` listing the phase-one sources (Jobcode, Himalayas, Remotive, RemoteOK, Indeed, Naukri, Glassdoor, ATS boards, and the two existing LinkedIn profiles), each with identifier, name, fetch method, enabled flag and method settings; verify the file is readable and every existing source identifier matches a row in the live `sources` table
- [x] 3.2 Implement the registry loader and validator (missing fields, duplicate identifiers, unknown fetch methods, secrets in the file); verify unit tests cover each rejection case from the source-registry spec
- [x] 3.3 Document the registry format and how to add, disable or re-enable a source or LinkedIn profile in `docs/source-registry.md`; verify a new entry added by following the doc passes validation

## 4. Settings and secrets

- [x] 4.1 Write `config/settings.yaml` with run limits, retry counts, pacing, health thresholds, scoring weights, hiring marker phrases, field aliases, notification channel, trigger wait and polling limits, repeat-trigger behaviour and schedule hint, with a comment on every key; verify the loader reads it and rejects unknown or invalid values
- [x] 4.2 Implement reading per-service token lists, the `TRIGGER_SECRETS` list and other secrets from the environment, failing with a message that names the missing variable; verify unit tests cover a missing, single-value and multi-value list
- [x] 4.3 Document every setting and every required secret name in `docs/configuration.md`, marking which secrets belong in Render environment variables and which two (trigger URL and one trigger secret) belong in GitHub; verify each setting in the file appears in the doc

## 5. Credential pool

- [x] 5.1 Implement the pool holding an ordered token list per service and marking tokens unavailable for the run; verify unit tests cover several tokens, a single token and all-unavailable
- [x] 5.2 Implement rotation on quota, rate-limit or rejected-token failures through a per-service classifier, retrying with the next token and never rotating for unrelated errors; verify unit tests cover rotation, no rotation on a malformed request, and skipping an unavailable token on later calls
- [x] 5.3 Redact token values from all logs and error messages; verify a test fails if any token value appears in captured log output

## 6. Persistence foundation

- [x] 6.1 Read from the live database (read-only) the allowed `source_runs.status` and `sources.access_method` values, whether `jobs.dedupe_key` has a unique constraint, and a sample of existing dedupe keys; record the results in `docs/database-notes.md` and verify the notes match query output
- [x] 6.2 Write migration files for a default on `runs.run_id`, a seen-posts table with row-level security enabled and no public policy, and a unique index on `jobs.dedupe_key` only if 6.1 shows it missing; verify each file is safe to run twice by reading it, and do not apply anything
- [x] 6.3 Implement the database client wrapper, the job repository (upsert by dedupe key, update last-seen, source link per source), the run repository (run and per-source rows), and the seen-post repository; verify unit tests with a fake client cover repeated writes producing no duplicates
- [x] 6.4 Implement stale-job retirement using `max_job_age_days` and the last-seen window from settings; verify a unit test marks an old job inactive and leaves a recent one active

## 7. Processing

- [x] 7.1 Implement the dedupe key builder that reproduces the live key format; verify it reproduces at least ten live keys from 6.1 exactly
- [x] 7.2 Implement listing validation (title, company and apply URL required) and company exclusion with counted, reasoned discards; verify unit tests cover each rejection
- [x] 7.3 Implement normalisation of location bucket, work mode, employment type, experience range, salary in lakhs, skills and posting date; verify unit tests cover stated salary, missing fields and the unknown-value case

## 8. Fetching framework

- [x] 8.1 Define the fetcher interface and the common raw listing shape; verify a fake fetcher satisfies the interface in a unit test
- [x] 8.2 Implement the shared wrapper for pacing, bounded retries, timeouts and per-source failure isolation, recording blocked sources without attempting to bypass them; verify unit tests cover transient recovery, retries exhausted, a login wall recorded as blocked, and one failing source not stopping the next
- [x] 8.3 Implement the fetcher factory mapping each fetch method to its class from a lookup table; verify an unknown method raises the invalid-registry error and a new entry resolves without editing the factory logic

## 9. Open API and feed fetchers

- [x] 9.1 Implement the Jobcode fetcher against its WordPress JSON posts endpoint using the last successful time; verify a contract test against a saved sample payload returns the expected listings
- [x] 9.2 Implement the Himalayas fetcher honouring its limits and keeping its source name and original link; verify a contract test against a saved sample payload
- [x] 9.3 Implement the Remotive fetcher with a configurable daily call cap and the 24-hour delay noted, skipping extra calls the same day; verify a unit test shows the cap holds across repeated runs
- [x] 9.4 Implement the RemoteOK fetcher that skips the legal notice object, keeps the original URL and credits the source; verify a contract test against a saved sample payload
- [x] 9.5 Document each open source's limits and attribution rules in `docs/sources.md`; verify each fetcher's rules are listed there

## 10. Company ATS board fetchers

- [x] 10.1 Implement the Greenhouse, Lever and Ashby board fetchers taking company slugs from the registry; verify contract tests against saved sample payloads for each
- [x] 10.2 Add a starter list of company slugs to `config/sources.yaml` supplied by the owner and verify each slug fetches without error in a dry run

## 11. Job board fetcher (JobSpy)

- [x] 11.1 Implement the JobSpy fetcher for Indeed, Naukri and Glassdoor with India country and city settings, search terms from `search_config`, and block detection that records a blocked board; verify unit tests with a mocked library cover results, a 429 or 403, and an empty result
- [x] 11.2 Add the `--only-methods` and `--only-sources` options needed to run this subset alone; verify a test shows only the selected sources are fetched

## 12. LinkedIn post ingestion

- [x] 12.1 Implement the Apify profile-post fetcher using the credential pool and the per-run post cap; verify unit tests with a mocked client cover newest-N posts, a disabled profile and the cap being enforced
- [x] 12.2 Implement the hiring-post recogniser and labelled-field parser using the marker phrases and aliases in settings; verify unit tests using the Oracle and Stripe example posts and the cheatsheet post as fixtures (accepted, accepted, ignored), and an unparseable case recorded as unparsed
- [x] 12.3 Implement short-link resolution using plain public requests, falling back to the original link flagged unresolved; verify unit tests against saved `lnkd.in` pages for Oracle and Stripe return their employer URLs and a failed fetch keeps the short link
- [x] 12.4 Wire the seen-posts repository so processed posts are skipped and every job keeps its profile and post URL; verify a test processes the same post twice and creates one job
- [x] 12.5 Document how to add an influencer profile and extend the marker phrases and aliases in `docs/linkedin-profiles.md`; verify a profile added by following the doc passes registry validation

## 13. Fit scoring

- [x] 13.1 Implement the rules scorer (keywords and skills, location, experience against the maximum, salary against the minimum, undisclosed salary neutral) producing a 1–5 score and a reason; verify unit tests cover each criterion and that identical input gives identical output
- [x] 13.2 Add internship and batch-restricted detection that lowers the score and states it in the reason; verify a test with the Stripe intern example flags it
- [x] 13.3 Implement the optional Gemini scorer for borderline jobs using the credential pool, minimal text, and fallback to rules on any failure, plus the scorer builder that keeps it off by default; verify unit tests cover disabled, enabled and available, and enabled with every token exhausted
- [x] 13.4 Make a scoring error store the job with a neutral score and a reason that scoring failed; verify a test raises inside the scorer and the job is still stored

## 14. Health and notifications

- [x] 14.1 Implement source health evaluation from recent `source_runs` and reuse `consecutive_empty_runs` and `last_success_at`; verify unit tests cover a normal source, a source at zero for the configured number of runs, and one far below baseline
- [x] 14.2 Implement missed-run detection from the latest run time and the configured hours; verify a unit test with a stale run time raises the alert
- [x] 14.3 Implement the notifier interface and the ntfy.sh notifier, with one summary message per run listing the count, best matches and problem sources; verify unit tests with a fake transport cover a run with new jobs and an unreachable channel that does not fail the run
- [x] 14.4 Add the optional heartbeat ping on success; verify a test shows it is called after a successful run and skipped when no URL is configured

## 15. Orchestration

- [x] 15.1 Implement the composition root that builds the pipeline from the registry, settings and credential pools; verify a test constructs it with fakes and no network
- [x] 15.2 Implement the daily pipeline (load, sync registry into `sources`, fetch, validate, normalise, dedupe, score, persist, health, notify) with a client-generated run id and per-source status rows; verify an end-to-end test with fake fetchers and a fake database produces the expected run and source records
- [x] 15.3 Implement the registry-to-`sources` sync that writes only identifier, name, base URL and enabled for existing rows and maps access method for new rows from the values found in 6.1; verify a test shows no other column is changed
- [x] 15.4 Implement the entry point with `--dry-run`, `--only-sources`, `--only-methods` and `--check-health-only`; verify each option in a test, including that `--dry-run` writes nothing
- [x] 15.5 Document the architecture, the run order, the command-line options and the service endpoints in `docs/architecture.md`; verify each documented command runs as written against fakes

## 16. Hosted service, triggers and local runs

- [x] 16.1 Implement the run manager in `service/`: starts the pipeline in a background thread, allows one active run through an in-process lock plus a check of `runs`, returns the active run's id on a second start, applies the configured repeat-trigger behaviour, and reports a run left marked running after a restart as interrupted; verify unit tests with a fake pipeline cover start, overlap refusal, finish, failure and restart
- [x] 16.2 Implement the endpoints (start returning 202 with a run id, run status, health check, unauthenticated liveness with no data) and shared-secret authentication against the `TRIGGER_SECRETS` list using constant-time comparison and no secret in logs or responses; verify tests with the framework's test client cover a missing secret, a wrong secret, either of two valid secrets, and that no secret appears in captured output
- [x] 16.3 Write the Render deployment definition (`render.yaml` or equivalent with no secret values, start command, health-check path) and the Windows Task Scheduler recipe for running only the job-board sources from the owner's PC; verify the files parse and contain no secret values
- [ ] 16.4 Run the Render spike: deploy the service with a fake pipeline that runs about 12 minutes, then measure the cold-start time, whether the run completes with status polling every minute, whether it completes with no incoming requests, and whether and when the free instance spins down mid-run; also read the free plan's hours and bandwidth limits from Render's dashboard; record the results in `docs/deployment.md` and decide between the service and the fallback; verify the recorded numbers come from observed logs and status calls
- [x] 16.5 Write the daily trigger GitHub Actions workflow with an off-peak cron minute, manual dispatch, a concurrency guard, a job timeout, retry-with-backoff on start for the configured wait, status polling until finished or the configured limit, a failing exit with the run id on timeout or failure, and only the trigger URL and trigger secret from repository secrets; verify the file passes a syntax check, lists no secret values and a dry run against a local copy of the service shows the retry and polling behaviour
- [x] 16.6 Write the health-check trigger workflow that calls the health-check endpoint at a different hour with the same retry behaviour; verify the file passes a syntax check
- [x] 16.7 Write the fallback workflow that runs the CLI inside the GitHub Actions job (manual dispatch only until needed, with pipeline secrets from repository secrets) and document the switch to it, including which workflow gets the schedule; verify the file passes a syntax check
- [x] 16.8 Document in `docs/deployment.md` the Render service setup and environment variables, the two GitHub secrets, rotating a trigger secret, private repository setup, the cold-start and polling behaviour, the fallback switch, and running the job-board sources from the owner's PC; verify each step is complete and in order by reading it end to end

## 17. Integration and rollout

- [x] 17.1 Run the full pipeline with `--dry-run` against the live database and verify the printed counts, dedupe keys and scores look right for at least one source of each fetch method
- [x] 17.2 Run the Apify spike on one profile with a small post limit and verify the actor returns full post text with the `lnkd.in` link intact; adjust the parser if it does not
- [ ] 17.3 Run the JobSpy spike from the deployed Render service and verify whether Indeed, Naukri and Glassdoor return results; record the outcome in `docs/database-notes.md` and set which boards run from the owner's PC
- [x] 17.4 After the owner approves, apply the migrations to the live database and verify each change by querying the schema
- [ ] 17.5 Enable the daily trigger workflow alongside the Claude routine for several days and verify coverage matches or exceeds the routine's per source from the `source_runs` records
- [ ] 17.6 Ask the owner for explicit approval before disabling the Claude routine, then disable it and verify the schedule no longer shows it as enabled

## Workflow follow-up

- Archive the change after the owner has approved parity and the project's review is complete.
- Verify the archived result.
