## 1. Preparation

- [x] 1.1 Archive `setup-project-foundation` (`openspec archive setup-project-foundation`) and confirm `openspec/specs/` now holds `project-tooling`, `static-site-delivery` and `content-source`. Then `openspec validate implement-ui --strict` passes
- [x] 1.2 Create a local `.env.local` with `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `APP_PASSWORD` and a ≥32-character `SESSION_SECRET` (never committed)

## 2. Unwind the static-export foundation (design D1, D2)

- [x] 2.1 In `next.config.ts` remove `output`, `trailingSlash` and `images.unoptimized`, and keep `typedRoutes`
- [x] 2.2 Delete `src/app/sitemap.ts`, `src/content/`, `src/lib/content.ts` and `src/lib/routes.ts`. Reduce `src/lib/site.ts` to `siteName`, and remove the `out/` directory
- [x] 2.3 Remove the content `no-restricted-imports` block from `eslint.config.mjs`, and add `scripts/**` linting if it isn't already covered
- [x] 2.4 Rewrite `src/app/robots.ts` to always return `Disallow: /`. In the root `layout.tsx` set `robots: { index: false, follow: false }`, drop `metadataBase` and canonicals, and add `color-scheme: light`
- [x] 2.5 `package.json`: remove `preview`, add `start` (`next start`), `test` (`vitest run`), `db:types`, `seed` and `seed:clean`, and add `test` to `check`
- [x] 2.6 Add dependencies `@supabase/supabase-js`, `server-only` and `zod`, and dev dependencies `vitest` and `tsx`. Review any new ignored build scripts in `pnpm-workspace.yaml`, then confirm `pnpm install --frozen-lockfile` succeeds
- [x] 2.7 Verify `pnpm build` succeeds with no env vars set, and that `pnpm start` serves on `PORT`

## 3. Core libraries (design D3, D4, D10)

- [x] 3.1 `src/lib/env.ts` (server-only): typed getters for the four secrets. `authConfigured()` returns false when `APP_PASSWORD` is missing or `SESSION_SECRET` is shorter than 32 characters
- [x] 3.2 Generate `src/lib/db/database.types.ts` with `pnpm db:types` (or Supabase MCP `generate_typescript_types`) and commit it
- [x] 3.3 `src/lib/db/domain.ts`: `as const` value arrays and label maps for app status, role track, location bucket, work mode, access method and run status, matching the CHECK constraints in data-access
- [x] 3.4 `src/lib/db/client.ts`: server-only typed Supabase client (no session persistence). Add a cached `getSourceNames()` that maps id → name and falls back to the id
- [x] 3.5 `src/lib/dates.ts`: `todayIST()`, `relativeTime()`, `isWithin24h()` and `formatDateIST()`, with vitest tests including the 00:30 IST / 19:00 UTC case
- [x] 3.6 `src/lib/auth/token.ts`: `sign({exp})` and `verify(token)` using HMAC-SHA256 and `timingSafeEqual`, with tests for valid, tampered, malformed, expired and rotated-secret tokens

## 4. Access gate (spec: access-gate)

- [x] 4.1 `src/lib/auth/session.ts`: create, read and clear the session cookie (HttpOnly, SameSite=Lax, Secure in prod, 30 days), plus `requireSession()`, which redirects pages and throws in actions
- [x] 4.2 `src/proxy.ts`: redirect to `/login?next=<path+query>` when there is no valid token. The matcher excludes `_next/static`, `_next/image`, `favicon.ico`, `robots.txt`, `api/health` and `login`
- [x] 4.3 `(auth)/login/page.tsx` plus a login action: fail-closed config message, digest + `timingSafeEqual` comparison, fixed 1s delay on failure, same-origin `next` validation, and redirect away when already logged in
- [x] 4.4 Logout Server Action that clears the cookie and redirects to `/login`
- [x] 4.5 `api/health/route.ts` returning 200 `{ "ok": true }` without touching the DB

## 5. App shell and styling (spec: app-hosting; design D11)

- [x] 5.1 Replace the `@theme` tokens in `globals.css` with the light palette (surface, muted, border, text, text-muted, accent, success, warning, danger), check AA contrast, and add focus-visible and 44px target utilities
- [x] 5.2 `(app)/layout.tsx`: header with Feed / Tracker / Sources / Settings links, a current-section marker, logout, and `<main>`. It must fit at 360px
- [x] 5.3 `src/app/not-found.tsx` (404 page with a link to the feed) and `global-error.tsx`, plus `(app)/error.tsx` with a "Try again" reset
- [x] 5.4 Shared components: `Badge`, `Button`/link styles, and a `Toast` live region

## 6. Source health banner (spec: source-health; design D9)

- [x] 6.1 Query: enabled sources plus recent runs, reduced to the latest run per source (pure reducer with unit tests)
- [x] 6.2 `LoginBanner` in the `(app)` layout inside `<Suspense>`, catching all errors and rendering one alert per `needs_login`/`captcha` source, linked to `/sources`

## 7. Feed (spec: job-feed; design D5, D6, D8)

- [x] 7.1 `src/lib/feed/params.ts`: parse and serialize `FeedFilters`, with defaults, invalid-value dropping and page reset. Unit tests cover the default view, the bookmarked view, invalid params, repeatable params and round-tripping
- [x] 7.2 Search sanitizing plus `or()` filter builders (q with skill case variants, source `links.cs`, posted-within with the `first_seen_at` fallback), with unit tests including `c++, (java)`
- [x] 7.3 Feed query on `job_feed`: `is_active`, filters, the three sort orders with `nullsLast` and an `id` tie-breaker, `.range()` with an exact count, and a parallel "New today" count
- [x] 7.4 Formatters: YOE text, salary text or "Salary not disclosed", fit "n/5" or "Not scored", posted or "Seen …" relative date, skills "+N". Unit tests for each
- [x] 7.5 `JobCard` server component with every field from the "Job card contents" requirement, an Apply link (new tab, `noopener noreferrer`), source links, and a title link carrying `?from=`
- [x] 7.6 Application Server Actions `setStatus(jobId, saved|applied|skipped|unsave)` and `restoreApplication(jobId, snapshot)`: `requireSession`, zod validation, snapshot return, `applied_on` coalescing to IST today, preservation of other fields, `revalidatePath`
- [x] 7.7 `TriageActions` client island: `useOptimistic`, 44px buttons, Undo toast for 6s, revert plus an error on failure, and a no-JS form fallback
- [x] 7.8 `FilterPanel`: GET form, `<details>` on mobile with the active count, sidebar on `lg`, active-filter chips, "Reset filters", and sort select
- [x] 7.9 `(app)/page.tsx`: total count, "New today (N)" link, card list, Prev/Next pagination, past-last-page and empty states. `(app)/loading.tsx` shows a list skeleton

## 8. Job detail (spec: job-detail; design D7)

- [x] 8.1 `(app)/jobs/[id]/page.tsx`: UUID check (malformed or missing → `notFound()`), all fields, summary, every link, first/last seen, an inactive notice, and `generateMetadata` with title + company
- [x] 8.2 "Back to feed" built from a validated `from` param, defaulting to `/`
- [x] 8.3 Reuse the Apply link and `TriageActions` on the detail page
- [x] 8.4 Application form with `useActionState`: zod limits (200/200/5000), no future dates, Applied auto-fills today, "New" goes through a server-side confirm step and then deletes. Show a "Saved" confirmation and inline errors that keep the input

## 9. Tracker (spec: application-tracker)

- [x] 9.1 Query every job with an application record (via `job_feed` where `app_status <> 'new'`, active or not), grouped and ordered by `applied_on` desc nulls last, then `updated_at` desc. This needs `updated_at`: read it from `applications` alongside the view, joined by job id
- [x] 9.2 `(app)/tracker/page.tsx`: columns at `lg` and up; below that, tabs driven by `?tab=` (default `applied`) with counts; a "Closed" label; the empty state
- [x] 9.3 A per-entry status move form reusing the application action rules (Applied fills the date, other fields kept)

## 10. Sources and settings (specs: source-health, search-settings)

- [x] 10.1 `(app)/sources/page.tsx`: every source with its access-method label, requires-login, latest run (status, found, new, relative + IST time, duration, message), "No runs yet", and the last 5 runs in `<details>`
- [x] 10.2 Enable/disable toggle Server Action (form button) with `requireSession` and `revalidatePath`
- [x] 10.3 `src/lib/templates.ts`: `expandTemplate()` and `findUnknownPlaceholders()`, plus the list normalizer (trim, drop blanks, dedupe ignoring case), with unit tests including the spec examples
- [x] 10.4 `(app)/settings/page.tsx`: `search_config` form (one per line lists, numeric ranges, ≥1 keyword and location) that saves `updated_at` and shows "Saved" with the last-updated time
- [x] 10.5 Add-source form: id pattern and uniqueness error, required name, http(s) base URL, access-method select, checkboxes, notes, template validation
- [x] 10.6 Edit-source forms with a read-only id, placeholder help text, an example expansion from the first keyword and location, and no delete control

## 11. Seed data (design D12)

- [x] 11.1 `scripts/seed.ts`: production and missing-env guards, about 40 `[Sample]` jobs with `seed:` dedupe keys covering every bucket, track, mode, fit and salary state with varied `first_seen_at`, and `job_sources` on existing source ids. Idempotent upserts
- [x] 11.2 `seed:clean`: delete `applications`, then `job_sources`, then `jobs` for `seed:%`. Verify that running seed twice keeps the count unchanged and that clean removes everything

## 12. Deployment and docs (spec: app-hosting)

- [x] 12.1 Rewrite `render.yaml` per design D1 (runtime node, singapore, free, branch main, `autoDeployTrigger: commit`, health path, NODE_VERSION 24, four `sync: false` secrets)
- [x] 12.2 Rewrite `.env.example` with the four variables and placeholders, and remove `NEXT_PUBLIC_SITE_URL` and `SITE_INDEXING`
- [x] 12.3 README: local setup (corepack, pnpm install, `.env.local`, `db:types`, seed and seed:clean, dev, check), the Render Blueprint deploy steps, the Free-plan cold-start note, and the shared-database warning about sample data
- [x] 12.4 Update the `openspec/config.yaml` context: Render Web Service, server features allowed, `proxy.ts` auth, Supabase server-only access, no SEO or route registry or content layer, vitest in the quality gate

## 13. Verification

- [x] 13.1 `pnpm check` and `pnpm build` pass
- [x] 13.2 Secret check: after building with real env vars, grep `.next/static` and a rendered feed page's HTML for the service role key and the Supabase host, and find no matches
- [x] 13.3 With seeded data, use the `playwright-cli` skill at 360px and 1280px to walk through: login redirect with `next`, feed defaults, a bookmarked filter URL, Save / Applied / Skip with Undo, Apply opening a new tab, detail edit with validation errors, reset-to-new confirm, tracker tabs and move, source toggle, the banner (by inserting a `needs_login` test run and removing it afterwards), settings validation, logout, and keyboard focus through a card. Confirm no horizontal scroll at 360px
- [x] 13.4 Unauthenticated `curl` checks: `/api/health` returns 200, `/` returns a redirect to `/login`, and a POST to a Server Action without a cookie changes nothing
- [x] 13.5 `openspec validate implement-ui --strict` passes
