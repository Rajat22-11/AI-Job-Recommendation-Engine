## REMOVED Requirements

### Requirement: Content defined as typed data
**Reason**: The app has no editorial content pages. Everything it shows comes from the Supabase database.
**Migration**: Move the few remaining UI strings into components. Data access is covered by the `data-access` capability.

### Requirement: Single content access layer
**Reason**: Replaced by the server-only data access layer for Supabase.
**Migration**: See `data-access`.

### Requirement: Page metadata comes from content
**Reason**: Page titles are fixed per screen, plus the job title on job detail. No content entries remain.
**Migration**: Each route declares its own metadata.

### Requirement: Missing content fails the build
**Reason**: There are no build-time content lookups anymore.
**Migration**: A missing record at runtime renders the not-found page (see `app-hosting`).
