# Design

## Approach

The main specs were created by archiving `add-programmatic-job-aggregation`, so each correction is a requirement-level change to an existing main spec. Each one is written as a delta in this change: a MODIFIED block repeats the full requirement with the edit applied, and an ADDED block introduces a requirement that does not yet exist. The archive sync then replaces each MODIFIED requirement by its exact header, so every header in a delta must match the current main spec text.

## Decisions

- **Requirement-level changes only.** Behaviour that the specs describe is corrected. Facts that belong in configuration or in operating notes (library version pins, the trigger script's diagnostics, the Render plan) stay out of the specs and are recorded in the tasks.
- **No requirement is invented to make a delta fit.** Three capabilities (job-persistence, linkedin-post-ingestion, run-orchestration) already match the code for the eight revisions and get no delta.
- **Scenarios carry the behaviour.** Each new or changed rule has at least one scenario, so validation and the sync can check it.
- **Archived documents are a separate decision.** The archived `proposal.md`, `design.md` and `tasks.md` contain the outdated statements in plain text. Those files are history, so this change does not edit them by delta; the tasks ask for a decision on whether to correct them directly.

## Risks

- A MODIFIED header that does not match its main-spec header exactly is rejected by the sync. Mitigation: validate after the sync and compare requirement counts with the main specs.
- A MODIFIED block that drops a scenario from the main spec would lose it. Mitigation: each MODIFIED block repeats every scenario that still applies.
