## Purpose

Shows whether each job source is enabled and how its most recent scraper run went, and warns across the whole app when a source needs the user to log in again or solve a captcha before the next run.

## ADDED Requirements

### Requirement: Sources overview
The page `/sources` SHALL list every source with:
- name, base URL and access method label
- whether it requires login
- its enabled state
- its latest run: status, jobs found, new jobs, start time (relative and absolute in IST), duration when it has finished, and message

A source with no runs MUST show "No runs yet". Each source MUST also show its 5 most recent runs in a collapsed section.

#### Scenario: Latest run shown
- **WHEN** source "Naukri" last ran 2 hours ago with status `ok`, 40 found and 6 new
- **THEN** its row shows OK, 40 found, 6 new, and "2h ago"

#### Scenario: Never run
- **WHEN** a source has no `source_runs` rows
- **THEN** its row shows "No runs yet"

### Requirement: Enable or disable a source
Each source on `/sources` SHALL have a toggle that sets `enabled`. The change MUST be saved immediately and reflected after a reload.

#### Scenario: Disabling a source
- **WHEN** the user switches "LinkedIn" off
- **THEN** `sources.enabled` for that source is false, and the page shows it as disabled after a reload

### Requirement: Login-needed banner
Every authenticated page SHALL show a banner at the top for each enabled source whose latest run has status `needs_login` or `captcha`. The banner reads "Log in to <name> in Chrome before the next run." and links to `/sources`. Disabled sources and sources whose latest run has any other status MUST NOT trigger the banner.

#### Scenario: Captcha on latest run
- **WHEN** enabled source "Naukri" has a latest run with status `captcha`
- **THEN** every page, including the feed, shows "Log in to Naukri in Chrome before the next run."

#### Scenario: Resolved by a later run
- **WHEN** a source's earlier run was `needs_login` but its latest run is `ok`
- **THEN** no banner is shown for that source

#### Scenario: Disabled source
- **WHEN** a disabled source's latest run is `needs_login`
- **THEN** no banner is shown for it

#### Scenario: Banner data unavailable
- **WHEN** loading run data for the banner fails
- **THEN** the page still renders without the banner
