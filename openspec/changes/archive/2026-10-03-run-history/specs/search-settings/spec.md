## ADDED Requirements

### Requirement: Settings last used by a run
Next to "Last updated", the search configuration form SHALL show "Last used by run <first 8 characters of run_id> at <time in IST>" for the most recently started run, found in `runs` or `source_runs`, linking to that run on `/runs`. When `search_config.updated_at` is later than that run's start, it MUST add "Changed after this run, applies from the next run." When there are no runs, it MUST show "Not used by any run yet". After a save, the note MUST reflect the new last-updated time without a reload.

#### Scenario: Settings unchanged since the last run
- **WHEN** the settings were last updated on 1 Oct and the latest run started on 3 Oct at 09:00 IST
- **THEN** the form shows "Last used by run 1a2b3c4d at" followed by 3 Oct 09:00 IST in the same format as "Last updated", and no "Changed after this run" note

#### Scenario: Settings changed after the last run
- **WHEN** the user saves the settings after the latest run started
- **THEN** the form shows "Changed after this run, applies from the next run."

#### Scenario: No runs
- **WHEN** neither `runs` nor `source_runs` has any rows
- **THEN** the form shows "Not used by any run yet"
