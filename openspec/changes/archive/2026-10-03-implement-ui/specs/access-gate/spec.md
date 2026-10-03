## Purpose

Restricts the whole app to its single owner with one shared password, so job data and application notes are never visible to anyone else on the public internet.

## ADDED Requirements

### Requirement: Every route requires a session
Every page and every data-changing action SHALL require a valid session, except the login page, `/api/health`, `robots.txt`, and static framework assets. A page request without a valid session MUST redirect to the login page and keep the originally requested path and query so the user can return to it. A data-changing action without a valid session MUST be rejected without changing any data, even if it is called directly rather than through the UI.

#### Scenario: Unauthenticated page request
- **WHEN** a visitor without a session requests `/tracker`
- **THEN** they are redirected to the login page, which carries a return target of `/tracker`

#### Scenario: Filters preserved through login
- **WHEN** a visitor without a session opens `/?track=ml_ai&fit=4` and then logs in successfully
- **THEN** they land on `/?track=ml_ai&fit=4`

#### Scenario: Direct action call without session
- **WHEN** a request invokes the "mark applied" action without a valid session cookie
- **THEN** no application row is created or changed, and the request fails

### Requirement: Password login
The login page SHALL accept a single password and compare it with the `APP_PASSWORD` environment variable using a constant-time comparison. A wrong password MUST show a generic error that doesn't reveal anything about the correct password. A short fixed delay MUST apply to every failed attempt. The return target MUST be accepted only when it is a same-origin relative path. Anything else falls back to the feed.

#### Scenario: Correct password
- **WHEN** the user submits the correct password
- **THEN** a session is created and they are taken to the return target, or to the feed if there is none

#### Scenario: Wrong password
- **WHEN** the user submits an incorrect password
- **THEN** no session is created, the message "Incorrect password" is shown, and the response arrives no sooner than the fixed delay

#### Scenario: Open-redirect attempt
- **WHEN** the login form is submitted with a return target of `https://evil.example` or `//evil.example`
- **THEN** after a successful login the user lands on the feed

#### Scenario: Already logged in
- **WHEN** a user with a valid session opens the login page
- **THEN** they are redirected to the feed

### Requirement: Signed session cookie
A session SHALL be stored in a cookie that is `HttpOnly`, `SameSite=Lax`, `Path=/`, and `Secure` in production. Its value MUST carry an expiry and a signature computed with `SESSION_SECRET`. A cookie with a bad signature, a malformed value or a past expiry MUST be treated as no session. Sessions MUST expire 30 days after login. Changing `SESSION_SECRET` MUST invalidate every existing session.

#### Scenario: Tampered cookie
- **WHEN** a request carries a session cookie whose payload was altered after signing
- **THEN** the request is treated as unauthenticated

#### Scenario: Expired session
- **WHEN** a request carries a correctly signed session cookie whose expiry is in the past
- **THEN** the request is treated as unauthenticated

#### Scenario: Secret rotation
- **WHEN** `SESSION_SECRET` is changed and the service restarts
- **THEN** previously issued session cookies no longer authenticate

### Requirement: Logout
Every authenticated page SHALL offer a logout control. Logout MUST clear the session cookie and redirect to the login page.

#### Scenario: Logging out
- **WHEN** the user activates logout
- **THEN** the session cookie is cleared, they are on the login page, and opening the feed again redirects back to login

### Requirement: Fail closed on missing configuration
If `APP_PASSWORD` or `SESSION_SECRET` is missing at runtime, or `SESSION_SECRET` is shorter than 32 characters, no session SHALL be accepted or issued, and the login page MUST say that the server isn't configured.

#### Scenario: Missing password variable
- **WHEN** the app runs without `APP_PASSWORD` and someone submits the login form
- **THEN** no session is created and a configuration error message is shown

#### Scenario: Weak secret
- **WHEN** the app runs with a 16-character `SESSION_SECRET`
- **THEN** existing cookies are rejected, login is refused, and the configuration error is shown
