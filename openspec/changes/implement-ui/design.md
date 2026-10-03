## Context

The repository holds the `setup-project-foundation` scaffold: Next.js 16.3 App Router, React 19, strict TypeScript, Tailwind v4, pnpm 12 and Node 24. That scaffold is set up as a static export for a Render Static Site, with SEO plumbing and a content layer. No Render service has been created yet. Nothing is deployed, so nothing needs migrating.

The database is the existing Supabase project "Jobs Recommendation Engine" (`ooqayggwtfhrqhsovbhd`, ap-south-1, Postgres 17). Facts about it that shape this design:
- Status-like columns are `text` with CHECK constraints, not enums, so generated types give back plain `string`.
- `job_feed` is a plain view: `jobs` LEFT JOIN `applications`, `COALESCE(status,'new')`, and `links` built as a jsonb array of `{source: <source_id>, url}`.
- RLS is enabled on every table with no policies, so only the service role can read or write. `job_feed` is created with `security_invoker = true`, so it inherits that RLS. Verified on 2026-10-03: the publishable key reads `[]` from every table and from the view, and its inserts are rejected (`42501`). Any future recreation of the view must keep `security_invoker = true`, or the view would expose its rows to the public key.
- Existing indexes: `jobs (is_active, fit_score desc, posted_at desc)`, `jobs (location_bucket)`, `jobs (role_track)`, `job_sources (job_id)`, `source_runs (source_id, started_at desc)`.
- `jobs` currently has 0 rows. `sources` has 5, `source_runs` has 10.
- There is a **single** Supabase project. Development and production share one database.

In Next 16, `middleware.ts` is deprecated in favor of `proxy.ts`, which always runs on the Node.js runtime.

## Goals / Non-Goals

**Goals:**
- Server-rendered pages with little client JavaScript: Server Components for reads and Server Actions for writes. Only quick triage and Undo use client islands.
- One trustworthy auth check that every page and action goes through.
- Feed queries that stay a single round trip per data set, using the existing indexes.
- Pure, unit-testable modules for every rule that's easy to get wrong: param parsing, session tokens, IST dates, template expansion, list normalization.

**Non-Goals:**
- Any schema object: RPC, view, index or policy. If one becomes necessary it belongs in a separate change to the scraper's repository.
- A data-fetching or state library, a UI kit, or an auth library.
- End-to-end test infrastructure. Verification uses the `playwright-cli` skill manually, as described in tasks.md.
- Fixing Free-plan cold starts.

## Decisions

### D1. Next.js server runtime on a Render Web Service (replaces foundation D1)
Remove `output: "export"`, `trailingSlash` and `images.unoptimized`, and keep `typedRoutes`. Leave `cacheComponents` off: every app page reads cookies or search params, so pages render dynamically on each request, which is the behavior wanted here. `render.yaml`:

```yaml
services:
  - type: web
    name: ai-job-recommendation-ui
    runtime: node
    region: singapore        # can't be changed after creation
    plan: free
    branch: main             # Render's default is master
    autoDeployTrigger: commit
    buildCommand: pnpm install --frozen-lockfile && pnpm build
    startCommand: pnpm start
    healthCheckPath: /api/health
    previews:
      generation: off
    envVars:
      - key: NODE_VERSION
        value: "24"
      - { key: SUPABASE_URL, sync: false }
      - { key: SUPABASE_SERVICE_ROLE_KEY, sync: false }
      - { key: APP_PASSWORD, sync: false }
      - { key: SESSION_SECRET, sync: false }
```

`next start` reads `PORT`, and Render sets it. Field names were checked against Render's Blueprint reference while exploring: `autoDeployTrigger` replaces the deprecated `autoDeploy`, and `singapore` is a valid region. Render's image already provides a corepack-managed `pnpm` in `/usr/bin`, which is read-only, so `corepack enable` fails there with `EROFS` (found on the first deploy, 2026-10-03). The commands call `pnpm` directly, and it uses the version pinned in `packageManager`.
- **Alternative:** `npm ci` / `npm run start`, as written in the original brief. Rejected because the repo is pnpm-only (`project-tooling`) and has no `package-lock.json`.
- **Alternative:** keep the static site and add a separate API service. Rejected: two services, CORS, and the auth cookie would cross origins.

### D2. Route layout
```
src/
  proxy.ts                         auth redirect (D3)
  app/
    layout.tsx                     <html>, fonts, robots noindex, light color-scheme
    robots.ts                      Disallow: /
    not-found.tsx, global-error.tsx
    api/health/route.ts            200 {"ok":true}, no DB access
    (auth)/login/page.tsx          password form, useActionState
    (app)/layout.tsx               header nav + logout + <Suspense> login banner
    (app)/page.tsx                 feed      + loading.tsx + error.tsx
    (app)/jobs/[id]/page.tsx       detail    + not-found.tsx
    (app)/tracker/page.tsx
    (app)/sources/page.tsx
    (app)/settings/page.tsx
  lib/
    env.ts                         server-only, typed + validated env access
    auth/token.ts                  pure sign/verify (unit-tested)
    auth/session.ts                cookie read/write, requireSession()
    db/client.ts                   server-only supabase client (service role)
    db/database.types.ts           generated, committed
    db/domain.ts                   value unions + labels mirroring CHECKs
    db/queries/*.ts                feed, job, tracker, sources, settings
    feed/params.ts                 parse ⇄ serialize URL filters (unit-tested)
    dates.ts                       IST helpers (unit-tested)
    templates.ts                   URL template expand/validate (unit-tested)
    actions/*.ts                   'use server' modules
  components/                      JobCard, TriageActions (client), FilterPanel, Badge, …
scripts/seed.ts
```
The route groups `(auth)` and `(app)` let the login page skip the authenticated shell and the banner query. Removed from the foundation: `sitemap.ts`, `src/content/`, `lib/content.ts`, `lib/routes.ts`, most of `lib/site.ts` (only `siteName` survives), the `no-restricted-imports` content rule, and the `preview` script.

### D3. Auth: HMAC token, proxy redirect, and a guard in every action
- **Token:** `base64url(JSON{exp}) + "." + base64url(HMAC-SHA256(SESSION_SECRET, payload))`, verified with `crypto.timingSafeEqual`. It needs no library, and `node:crypto` is available because `proxy.ts` runs on Node. The payload holds only `exp`, since there's a single user. Lifetime is 30 days.
- **Cookie:** `session`; HttpOnly, SameSite=Lax, Path=/, Secure when `NODE_ENV=production`.
- **`proxy.ts`:** the matcher excludes `_next/static`, `_next/image`, `favicon.ico`, `robots.txt`, `api/health` and `login`. Without a valid token it redirects to `/login?next=<path+query>`.
- **`requireSession()`** runs at the top of every Server Action and every `(app)` page. Next's docs warn that proxy-only auth can be bypassed, and Server Actions are reachable by direct POST. Calling it in every page as well as in the proxy is redundant, but cheap.
- **Login action:** checks env config (fail closed), compares SHA-256 digests of the input and of `APP_PASSWORD` with `timingSafeEqual` so length doesn't leak, waits a fixed 1s on failure, and accepts `next` only if it matches `^/(?!/)` and contains no `\`.
- **Alternative:** iron-session or Auth.js. Rejected: heavy for a single shared password.

### D4. Data access: supabase-js with the service role, server-only
`db/client.ts` imports `server-only` and creates one client per process with `auth: { persistSession: false, autoRefreshToken: false }`, typed by `Database`. Queries go through PostgREST. Every read for a page runs in parallel with `Promise.all`. `getSourceNames()` is wrapped in React `cache()` so it runs once per request.
- **Types:** `pnpm db:types` runs `pnpm dlx supabase gen types typescript --project-id ooqayggwtfhrqhsovbhd --schema public`, and the output is committed. The Supabase MCP `generate_typescript_types` gives the same file. `db/domain.ts` defines `as const` arrays for each CHECK set, plus their label maps. Query helpers narrow the generated `string` columns to these unions.
- **Alternative:** a direct Postgres connection with `postgres.js` and raw SQL. That would allow `DISTINCT ON` and `ILIKE ANY(skills)`, but the brief fixes the credentials to `SUPABASE_URL` and the service role key, and it adds pooler and SSL setup. Rejected for v1. Its cost is the skills-search limitation below.

### D5. Feed query composition
`feed/params.ts` turns `URLSearchParams` into a typed `FeedFilters`, dropping invalid values and applying defaults (`status=[new,saved]`, `fit=3`, `sort=fit`). `serialize()` goes the other way. Links omit default values so URLs stay short. The query runs on `job_feed`, with `{ count: 'exact' }` and `.range((page-1)*25, page*25-1)`:

| Filter | PostgREST |
|---|---|
| active | `.eq('is_active', true)` |
| track / loc / mode / status | `.in(col, values)` (skipped when `status=all`) |
| fit > 0 | `.gte('fit_score', n)` (nulls excluded naturally) |
| salary | `meets` → `.eq('salary_meets_min', true)`; `unknown` → `.is('salary_meets_min', null)` |
| source | `.or('links.cs.[{"source":"a"}],links.cs.[{"source":"b"}]')` |
| posted | `.or('posted_at.gte.D,and(posted_at.is.null,first_seen_at.gte.T)')` with D/T from IST "now − n days" |
| seen=24h | `.gte('first_seen_at', now−24h)` |
| q | `.or('title.ilike."*q*",company.ilike."*q*",skills.cs.{"q"},skills.cs.{"Q"},…')` |
| sort fit | `fit_score desc nullsLast`, `posted_at desc nullsLast`, `first_seen_at desc`, `id` |
| sort newest | `posted_at desc nullsLast`, `first_seen_at desc`, `id` |
| sort salary | `salary_max_lpa desc nullsLast`, `salary_min_lpa desc nullsLast`, `fit_score desc nullsLast`, `id` |

`id` is the final tie-breaker in every sort, which keeps pagination stable. Because several filters use `.or()`, each one is its own `.or()` call, and PostgREST ANDs separate `or` parameters together. Search text is trimmed, `*` `%` `_` `\` `"` `,` `(` `)` are stripped or escaped, and values are double-quoted. Skills match against case variants: as typed, lower, upper and capitalized (spec: job-feed "Text search"). The "New today" count is a separate `head: true` count query, run in parallel.

### D6. Quick triage: a client island with useOptimistic and snapshot Undo
`TriageActions` is the only client component in a card. It calls Server Actions `setStatus(jobId, 'saved'|'applied'|'skipped'|'unsave')`. Each action:
1. Runs `requireSession()`.
2. Reads the current `applications` row (the snapshot).
3. Upserts with `onConflict: 'job_id'`, setting status and `updated_at`, and setting `applied_on = coalesce(existing, todayIST)` for applied; `unsave` deletes the row.
4. Calls `revalidatePath('/')`.
5. Returns `{ ok, previous: snapshot | null }`.

`useOptimistic` shows the new state at once. A small toast region (`aria-live="polite"`) shows "Undo" for 6 seconds. Undo calls `restoreApplication(jobId, previous)`, which re-validates the snapshot with zod and either upserts it exactly or deletes the row when `previous` is null. The upsert only sends the columns it changes, so notes, resume version and referral contact are preserved.

Without JavaScript the buttons are still `<form action>` submissions. They work, but with no optimistic state and no Undo.
- **Alternative:** plain forms with no client island. Rejected: each tap would wait a full round trip, which feels slow on mobile data.

### D7. Job detail as a route; return links via `from`
Feed card links carry `?from=<serialized feed query>`. The detail page accepts `from` only when it parses as a feed query (it starts with `?` or is empty) and builds "Back to feed" from it. That keeps the user's filters and page without relying on browser history. The application form uses `useActionState`. Choosing "New" asks for a server-side confirmation: the first submit returns `needsConfirm`, and the form re-renders with a "Discard notes and reset" button. This works without JavaScript and avoids `window.confirm`.
- **Alternative:** a drawer, or an intercepting route `@modal/(.)jobs/[id]`. Deferred: on a 360px screen a full page gives the same experience with zero client JS, and the intercepting route can be added later without moving code.

### D8. Filters UI without JavaScript
`FilterPanel` is a GET `<form action="/">` of checkboxes, selects and a search input. It doesn't send `page`, so changing a filter resets pagination. On narrow screens it sits inside `<details><summary>Filters (n)</summary>`. On `lg` and up it's an always-open sidebar. Active filters also appear as removable chip links, each computed with `serialize()`.

### D9. Login banner in the `(app)` layout
The layout renders `<Suspense fallback={null}><LoginBanner/></Suspense>`. `LoginBanner` fetches the enabled sources, then the latest run for each one in parallel (`limit 1` per source, served by `source_runs_recent_idx`). PostgREST can't do `DISTINCT ON`, and a fixed "N most recent runs" window could miss a source that hasn't run lately. It renders one alert for each `needs_login`/`captcha`. Errors are caught and render nothing, so the banner can never break a page. The `/sources` page uses the same per-source query with `limit 5`. That's only 5 sources, so 5 small indexed queries.

### D10. Validation with zod; IST via Intl
Every form and action input is parsed with zod schemas that sit next to the actions. Each schema produces field-level error maps for `useActionState`. `dates.ts` uses `Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' })` to get today as `YYYY-MM-DD`, and computes relative times from `Date.now()`. It needs no date library. Tests pin "now" so they don't depend on the clock.

### D11. Styling
Replace the placeholder `@theme` tokens with a neutral light palette: surface, muted, border, text, text-muted, accent, success, warning, danger. Each must pass WCAG AA for text against the surface. Set `color-scheme: light` on `:root`, and add no `dark:` variants. Use a system font stack, so there's no font download. Touch targets use a shared `min-h-11 min-w-11` utility. Focus uses `focus-visible:outline` in the accent color.

### D12. Dev seed against the shared database
`scripts/seed.ts` runs with `tsx --env-file=.env.local`. It refuses to run when `NODE_ENV=production` or when keys are missing. It upserts about 40 jobs with `dedupe_key` prefixed `seed:` and titles prefixed `[Sample]`, spread across every bucket, track, mode, fit score and salary state, with `first_seen_at` ranging from 1 hour to 40 days ago. It attaches `job_sources` rows to existing source ids, with URLs under `https://example.com/seed/…` (unique on `url`, so re-runs are idempotent). `pnpm seed:clean` deletes `applications`, then `job_sources`, then `jobs` for `seed:%` keys.

### D13. Tests
Add `vitest`, running in node environment, for the pure modules: `feed/params`, `auth/token`, `dates`, `templates`, settings list normalization, and the YOE and salary formatters. `pnpm test` runs `vitest run`. `pnpm check` becomes lint + typecheck + format:check + test.

## Risks / Trade-offs

- **[Free plan cold start of about 30–60s after 15 minutes idle]** The user chose to accept this. The README documents it. If it becomes painful, the fix is a one-line `plan: starter` change, or an external uptime pinger hitting `/api/health`.
- **[Sample data is visible in production, because dev and prod share one database]** Seeded rows are prefixed `[Sample]` and `seed:`. The README says to run `pnpm seed:clean` before relying on real data. Seeding is a manual command, never automatic.
- **[Skill search is case-variant matching, not true case-insensitive]** A stored "PyTorch" doesn't match a typed "pytorch". This is accepted for v1. Fixing it fully needs an RPC or generated column in the scraper's schema (a separate change).
- **[Count `exact` on the view gets slower as jobs grow]** That's fine at the expected scale (thousands of rows). If it lags, switch to `count: 'estimated'` or drop the total.
- **[Undo snapshot passes through the client]** Only an authenticated user can call restore, and the snapshot is re-validated with zod. The worst case is the user overwriting their own row.
- **[Render's pnpm doesn't honor `packageManager`, or rejects the lockfile]** Fall back to `npx --yes pnpm@12.8.1 install --frozen-lockfile && npx --yes pnpm@12.8.1 build` and `startCommand: node_modules/.bin/next start`.
- **[Writes from the UI race with the scraper]** The scraper writes `jobs`, `job_sources` and `source_runs`. The UI writes `applications`, `sources.enabled` and `search_config`. The only shared writes are to `sources` and `search_config`, which the scraper is expected only to read. Confirm this with the scraper owner (the user).
- **[Service role key in a long-lived process]** It is read only in `server-only` modules. The task list includes a check that greps the build output for the key.

## Migration Plan

1. Archive `setup-project-foundation` so its specs exist in `openspec/specs/` and this change's deltas apply.
2. Implement, run `pnpm check` and `pnpm build` locally, and verify with seeded data.
3. In Render: New → Blueprint → select the repo, then enter the four `sync: false` secrets. The first deploy runs from `main`.
4. Smoke-test production: `/api/health` returns 200, logging in works, and the feed loads.
5. Rollback: revert the commit on `main`, and auto-deploy redeploys the previous build. There is no schema migration to undo.
