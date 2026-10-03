## REMOVED Requirements

### Requirement: Self-contained static output
**Reason**: The app now reads the database and runs Server Actions on each request, so it can't be a static export.
**Migration**: The app runs as a Node web service (`next start`). See the `app-hosting` capability.

### Requirement: Canonical trailing-slash URLs
**Reason**: The app is private and never indexed, so canonical URLs serve no purpose. Its URLs carry filter query strings and aren't public pages.
**Migration**: None. Routes use Next.js defaults with no trailing slash.

### Requirement: Site URL configuration
**Reason**: `NEXT_PUBLIC_SITE_URL` was used only for canonicals and the sitemap, and both are removed.
**Migration**: Remove `NEXT_PUBLIC_SITE_URL` from the environment. Absolute URLs aren't needed.

### Requirement: Not-found handling
**Reason**: Not-found handling moves to the server-rendered app.
**Migration**: See "Not-found and error pages" in `app-hosting`.

### Requirement: Opt-in search indexing
**Reason**: A private, password-protected app must never be indexed, so there is nothing to opt into.
**Migration**: See "Never indexed" in `app-hosting`. Remove `SITE_INDEXING` from the environment.

### Requirement: Sitemap reflects registered routes
**Reason**: A private app has no public routes to list.
**Migration**: None. `sitemap.xml` is no longer served.
