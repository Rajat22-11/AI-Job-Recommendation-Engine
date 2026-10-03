## Purpose

Defines how the built site behaves when served by a static host: self-contained output, one canonical URL per page, proper not-found responses, and search-engine signals that stay off until launch.

## ADDED Requirements

### Requirement: Self-contained static output
The production build SHALL emit a directory of static files that a plain static file server can serve without a Node.js runtime. Every registered public route MUST be pre-rendered to its own HTML document.

#### Scenario: Served without a server runtime
- **WHEN** the `out/` directory is served by a generic static file server
- **THEN** every registered public route loads with its full HTML content and working styles

#### Scenario: Every registered route is emitted
- **WHEN** the build completes
- **THEN** an HTML document exists in `out/` for each route in the route registry

### Requirement: Canonical trailing-slash URLs
Every page URL SHALL use a trailing slash (for example `/jobs/`), and the root is `/`. Each page MUST declare an absolute canonical URL in trailing-slash form, built from the configured site URL. Internal links MUST point to the trailing-slash form.

#### Scenario: Canonical tag
- **WHEN** a page at path `/example/` is rendered with site URL `https://ai-job-recommendation-ui.onrender.com`
- **THEN** its HTML contains a canonical link to `https://ai-job-recommendation-ui.onrender.com/example/`

#### Scenario: Slash-less request
- **WHEN** a visitor requests the same page without the trailing slash
- **THEN** the page content is served and its canonical link still points to the trailing-slash URL

### Requirement: Site URL configuration
The canonical site URL SHALL be supplied through the `NEXT_PUBLIC_SITE_URL` build-time environment variable. A production build MUST fail with a clear message when it is missing or is not an absolute `https://` or `http://` URL.

#### Scenario: Missing site URL
- **WHEN** `pnpm build` runs without `NEXT_PUBLIC_SITE_URL`
- **THEN** the build fails and the error message names `NEXT_PUBLIC_SITE_URL`

### Requirement: Not-found handling
The build SHALL emit a not-found page. Requests for paths that match no route MUST receive that page with HTTP status 404 from any static host that honors a root `404.html`.

#### Scenario: Unknown path
- **WHEN** a visitor requests `/this-page-does-not-exist/`
- **THEN** the not-found page is shown with HTTP status 404

### Requirement: Opt-in search indexing
The site SHALL publish `robots.txt` and `sitemap.xml`. Unless the build-time variable `SITE_INDEXING` equals `true`, `robots.txt` MUST disallow all crawling and every page MUST carry a `noindex` robots directive. When indexing is enabled, `robots.txt` MUST allow crawling and reference the sitemap.

#### Scenario: Default build blocks indexing
- **WHEN** the site is built without `SITE_INDEXING=true`
- **THEN** `robots.txt` contains `Disallow: /` and pages include a `noindex` robots meta tag

#### Scenario: Launch build allows indexing
- **WHEN** the site is built with `SITE_INDEXING=true`
- **THEN** `robots.txt` allows crawling, includes the absolute sitemap URL, and pages carry no `noindex` directive

### Requirement: Sitemap reflects registered routes
`sitemap.xml` SHALL list the absolute canonical URL of every route in the route registry and no other URLs.

#### Scenario: Sitemap contents
- **WHEN** the registry contains only the home route and the site is built
- **THEN** `sitemap.xml` contains exactly one URL, the site root with a trailing slash
