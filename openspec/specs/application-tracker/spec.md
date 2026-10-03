# application-tracker Specification

## Purpose
An overview of every job the user has acted on, grouped by application status, so they can see their pipeline at a glance and follow up on applications.

## Requirements

### Requirement: Applications grouped by status
The tracker at `/tracker` SHALL list every job that has an application record, active or not, in groups in this order: Saved, Applied, Interview, Offer, Rejected, Skipped. Each group MUST show its count. Each entry MUST show the title (linking to the job detail page), the company, `applied_on` when set, and how long ago the record was last updated. Entries for inactive jobs MUST be labelled "Closed". Within a group, entries MUST be ordered by `applied_on` (newest first, undated last), then by last update (newest first).

#### Scenario: Counts
- **WHEN** the user has 4 saved, 6 applied and 1 interview application
- **THEN** the tracker shows Saved (4), Applied (6), Interview (1), Offer (0), Rejected (0), Skipped (0)

#### Scenario: Closed posting still tracked
- **WHEN** an applied job later becomes inactive
- **THEN** it still appears under Applied, labelled "Closed"

### Requirement: Columns on desktop, tabs on mobile
On wide viewports (1024px and wider) the tracker SHALL show the groups side by side as columns. On narrower viewports it MUST show one group at a time, with a tab for each group that carries its count. The selected tab MUST be stored in the URL (`?tab=<status>`), so it survives reloads and works without client-side JavaScript. The default tab is Applied.

#### Scenario: Mobile tab
- **WHEN** the tracker is opened at 360px wide with `?tab=interview`
- **THEN** only the Interview group is listed, and its tab is marked as selected

### Requirement: Move an application between statuses
Each tracker entry SHALL have a control that changes its status in place, applying the same rules as the detail form: moving to Applied with no date fills in today's IST date, and other fields are kept.

#### Scenario: Promote to interview
- **WHEN** the user changes an Applied entry's status to Interview
- **THEN** the entry moves to the Interview group, its `applied_on` is unchanged, and both counts update

### Requirement: Empty tracker
When there are no application records, the tracker SHALL show a message saying that saved and applied jobs will appear here, with a link to the feed.

#### Scenario: Fresh start
- **WHEN** no application records exist
- **THEN** the empty message and a link to the feed are shown
