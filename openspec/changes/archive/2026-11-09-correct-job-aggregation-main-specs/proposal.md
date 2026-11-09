# Proposal

## Why

The main specs created when `add-programmatic-job-aggregation` was archived describe an earlier design. They say the registry's enabled flag decides what runs, that Naukri is read through JobSpy, that the language-model scorer is off by default, and that keyword matching uses whole phrases. The code now does something different, so the specs mislead anyone who reads them and would send the next change in the wrong direction.

## What Changes

- The registry's `enabled` flag only sets the starting value for a source new to the database. The database flag decides what runs, so the UI toggle wins.
- A source enabled in the UI but not fetched is recorded as `skipped` with the reason from the `not_fetched` section of the registry. A source in neither place is recorded as `skipped` with a "not in the source registry" reason.
- Naukri is read through an Apify actor, not JobSpy. Glassdoor stays on JobSpy and is blocked. We Work Remotely, Working Nomads and Arc are fetched as public feeds or pages.
- Keyword matching is word-based: a keyword matches when the share of its significant words found in the title or skills reaches `prefilter_min_ratio` (0.3) for filtering, and `score_min_ratio` (0.5) for scoring. Description text alone never counts.
- Keyword match in scoring uses the title and skills only. A senior-sounding title with no stated years of experience is penalised.
- The language-model scorer is on by default for borderline (score 3) jobs, uses `gemini-3.5-flash-lite`, spaces its calls, falls back to rules when no key is set, and takes its wording from `config/gemini_prompt.yaml`.
- Local runs read secrets from `.env.local` or `.env`, with variables already set in the environment taking precedence.

No code changes. The four modified specs are corrected; the three others (job-persistence, linkedin-post-ingestion, run-orchestration) are already accurate for the eight revisions.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `source-registry`: the enabled flag is decided by the database once a source exists; a new "sources not fetched are recorded as skipped" requirement.
- `job-source-fetching`: the source list (Naukri via Apify, Glassdoor blocked, three new feeds and pages), and a new keyword-matching requirement.
- `job-fit-scoring`: keyword match on title and skills, the senior-title penalty, and the language-model scorer being on by default with pacing and a configurable prompt.
- `credential-pool`: a local `.env` scenario for reading tokens.

## Impact

- Main specs under `openspec/specs/` for the four capabilities above. Code, configuration and database are unchanged.
- The archived change's `proposal.md`, `design.md` and `tasks.md` contain the same outdated statements. Whether to correct them directly is a separate decision, recorded in `tasks.md`.
