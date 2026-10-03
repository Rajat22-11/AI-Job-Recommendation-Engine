## Why

A scraper already fills the Supabase project "Jobs Recommendation Engine" with job postings and source-run results, but the only way to see them is to query the database by hand. This change builds a personal, mobile-first web app for browsing the feed, applying in one tap, tracking applications, and keeping scraper sources healthy from a phone.

The current foundation is a public static export, and it can't do that job: the app needs request-time database reads, Server Actions, a password gate and secrets kept on the server. So this change also moves hosting from a Render Static Site to a Render Web Service, and removes the public-site plumbing (sitemap, opt-in indexing, canonicals, content layer) that a private app doesn't use.

## What Changes

- **BREAKING (hosting):** Remove `output: "export"`. The app is now served by `next start` on a **Render Web Service** (Node, region `singapore`, **Free plan**), defined in `render.yaml` with `autoDeployTrigger: commit` on branch `main`, a `/api/health` health check, and secrets declared `sync: false`. No Render service exists yet, so there's nothing to migrate.
- **BREAKING (public-site plumbing removed):** Delete `sitemap.ts`, the `SITE_INDEXING` toggle, trailing-slash canonicals, `NEXT_PUBLIC_SITE_URL`, the route registry, and the `src/content` layer with its lint rule. The app is always `noindex` and `robots.txt` disallows everything.
- Add a **password gate**: `APP_PASSWORD` login, an HMAC-signed httpOnly session cookie (`SESSION_SECRET`), a `proxy.ts` redirect (the Next 16 replacement for middleware), session checks inside every Server Action, and logout.
- Add **server-only data access** to the existing schema with `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. The schema is unchanged. TypeScript types are generated from it, and hand-written domain unions mirror its CHECK constraints.
- Add the **Feed** (home): job cards, Apply, quick Save / Applied / Skip with Undo, filters and sorting stored in URL search params, 25-per-page server pagination, and a "New today" preset in place of a separate digest page.
- Add **Job detail** as the route `/jobs/[id]`, with all fields, links and an editable application panel.
- Add the **Tracker**: applications grouped by status (columns on desktop, tabs on mobile).
- Add **Sources & health**: per-source enabled toggle and latest run, plus an app-wide banner when an enabled source needs a login or hit a captcha.
- Add **Settings**: edit `search_config`, and add or edit sources with placeholder help for search URL templates.
- Add a **dev seed script** that inserts sample jobs, because `jobs` is currently empty. It writes data only and never changes the schema.
- Add a **unit test runner** for pure logic: filter parsing, session signing, IST date handling.
- Update `.env.example`, the README (local setup and Render deploy), and the `openspec/config.yaml` project context.

## Capabilities

### New Capabilities
- `app-hosting`: Running as a Node web service on Render: Blueprint, health check, environment variables, always-noindex, not-found and error pages.
- `access-gate`: Single-user password login, signed session cookie, route protection, logout.
- `data-access`: Server-only Supabase access, generated and domain types, Asia/Kolkata date semantics.
- `job-feed`: Feed listing, card contents, quick actions, URL-driven filters and sort, pagination, "New today" preset, empty and loading states.
- `job-detail`: Job detail page and the application editing panel.
- `application-tracker`: Applications grouped by status, with counts and dates.
- `source-health`: Sources list with enabled toggle, latest-run status, and the app-wide login/captcha banner.
- `search-settings`: Editing `search_config`, and adding or editing sources.

### Modified Capabilities
- `project-tooling`: The build no longer writes `out/`. A `start` script, a type-generation script, a seed script and a test command are added.
- `static-site-delivery`: Removed. Replaced by `app-hosting`.
- `content-source`: Removed. App data comes from Supabase and there are no content pages.

These three capabilities come from `setup-project-foundation`, which is complete but not archived. It must be archived before this change so the deltas apply to `openspec/specs/`.

## Impact

- **Removed:** `src/app/sitemap.ts`, `src/content/`, `src/lib/content.ts`, `src/lib/routes.ts`, most of `src/lib/site.ts`, the `no-restricted-imports` content rule, the `preview` script, `out/`.
- **Modified:** `next.config.ts`, `render.yaml`, `.env.example`, `package.json`, `eslint.config.mjs`, `src/app/layout.tsx`, `src/app/robots.ts`, `src/app/globals.css` (light-theme tokens), `openspec/config.yaml` (context).
- **New:** `src/proxy.ts`, routes `/`, `/login`, `/jobs/[id]`, `/tracker`, `/sources`, `/settings`, `/api/health`, `src/lib/**` (auth, db, filters, dates), `src/components/**`, `scripts/seed.ts`, README.
- **Dependencies:** `@supabase/supabase-js`, `server-only`, `zod`; dev: `supabase` CLI (type generation), `vitest`, `tsx` (seed script).
- **External systems:** Supabase is read and written with the service role key, and RLS stays enabled with no policies. On Render's Free plan the instance spins down after about 15 minutes idle, so the first request after that takes roughly 30–60s. This is accepted.
- **Out of scope:** multi-user auth, auto-apply, resume tailoring, dark mode, schema changes, a separate digest page, a desktop drawer for job detail.
