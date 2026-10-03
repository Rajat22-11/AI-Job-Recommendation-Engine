# app-hosting Specification

## Purpose
Defines how the app is deployed and served: a Node web service on Render, defined by a Blueprint, with a health check, secrets kept out of the repository and the browser, no search indexing, and friendly not-found and error pages.

## Requirements

### Requirement: Render Blueprint for a Node web service
The repository SHALL contain a `render.yaml` Blueprint that defines exactly one web service. The service MUST have runtime `node`, region `singapore`, plan `free`, branch `main`, a build command that installs with the pinned pnpm from the frozen lockfile and builds, a start command that runs the production server, health check path `/api/health`, and automatic deploys on every commit to `main`. Node.js MUST be pinned to major version 24. The Blueprint MUST use field names from Render's current Blueprint specification (`autoDeployTrigger`, not the deprecated `autoDeploy`).

#### Scenario: Blueprint contents
- **WHEN** `render.yaml` is read
- **THEN** it declares one service with `type: web`, `runtime: node`, `region: singapore`, `plan: free`, `branch: main`, `autoDeployTrigger: commit`, `healthCheckPath: /api/health`, and `NODE_VERSION` set to 24

#### Scenario: Push to main deploys
- **WHEN** a commit is pushed to `main` after the Blueprint is applied
- **THEN** Render builds and deploys that commit without manual action

### Requirement: Secrets declared, never committed
The Blueprint SHALL declare `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `APP_PASSWORD` and `SESSION_SECRET` with `sync: false`, so their values are entered in the Render dashboard and never stored in the repository. The repository MUST contain an `.env.example` that lists every variable the app reads, with placeholder values only.

#### Scenario: No secret values in the repository
- **WHEN** `render.yaml` and `.env.example` are inspected
- **THEN** each of the four secrets appears only as a key (with `sync: false` in the Blueprint, or a placeholder in `.env.example`), never with a real value

### Requirement: Health endpoint
The app SHALL serve `GET /api/health` without authentication and return HTTP 200 with a small JSON body. The endpoint MUST NOT query the database, so a database outage does not take the service out of rotation.

#### Scenario: Health check while logged out
- **WHEN** an unauthenticated client requests `/api/health`
- **THEN** the response is 200 with a JSON body and no redirect

### Requirement: Never indexed
Every response SHALL carry signals telling search engines not to index the page. `robots.txt` MUST disallow all crawling. Every page MUST include a `noindex, nofollow` robots directive. No sitemap is served.

#### Scenario: robots.txt
- **WHEN** a crawler requests `/robots.txt`
- **THEN** the response disallows all paths for all user agents

#### Scenario: Page robots directive
- **WHEN** any page, including the login page, is rendered
- **THEN** its HTML contains a robots meta tag with `noindex` and `nofollow`

### Requirement: Not-found and error pages
Requests for unknown paths, and for job IDs that don't exist or aren't valid UUIDs, SHALL show a not-found page with HTTP status 404 and a link back to the feed. An unexpected server error while rendering a screen MUST show a friendly error message with a retry action instead of a blank page or stack trace, and the app navigation MUST still work.

#### Scenario: Unknown job
- **WHEN** a logged-in user opens `/jobs/<a well-formed UUID that matches no job>`
- **THEN** the not-found page is shown with status 404

#### Scenario: Malformed job id
- **WHEN** a logged-in user opens `/jobs/not-a-uuid`
- **THEN** the not-found page is shown with status 404 and no database error is logged

#### Scenario: Database unreachable
- **WHEN** the database request for the feed fails
- **THEN** the feed area shows an error message with a "Try again" action, and the header navigation still works

### Requirement: App navigation
Every authenticated page SHALL show a header with links to Feed, Tracker, Sources, Runs and Settings, with the current section marked, and a logout control. At 360px width the header MUST fit without horizontal scrolling.

#### Scenario: Navigating on a phone
- **WHEN** the app is viewed at 360px wide on any authenticated page
- **THEN** all five section links and logout can be reached, and the page doesn't scroll horizontally

### Requirement: Accessibility baseline
Pages SHALL use semantic landmarks (header, nav, main) and one `h1` per page. Every form control MUST have an accessible label. Every interactive element MUST be reachable by keyboard and show a visible focus indicator. Text MUST meet WCAG 2.2 AA contrast. Status MUST NOT be conveyed by color alone. Results of an action, such as "Saved", errors and Undo, MUST be announced to assistive technology.

#### Scenario: Keyboard-only triage
- **WHEN** a keyboard user tabs through a feed card
- **THEN** the title link, Apply, Save, Applied and Skip each receive visible focus in reading order, and each can be activated with Enter or Space

#### Scenario: Salary badge without color
- **WHEN** a job meets the minimum salary
- **THEN** its badge carries the text "Meets min", not only a green color
