# Job Tracker UI

A personal, mobile-first web app for browsing aggregated job postings and tracking applications. It reads and writes the existing Supabase project **Jobs Recommendation Engine**, which a separate scraper fills.

- **Feed** (`/`): active jobs with filters stored in the URL, one-tap Apply, and Save / Applied / Skip with Undo.
- **Job detail** (`/jobs/[id]`): every field, all source links, and an editable application record.
- **Tracker** (`/tracker`): applications grouped by status.
- **Sources** (`/sources`): enable or disable sources and see their latest scraper runs. A banner appears on every page when a source needs you to log in.
- **Settings** (`/settings`): edit the search configuration, and add or edit sources.

Stack: Next.js 16 (App Router, Server Components and Server Actions), React 19, TypeScript, Tailwind CSS v4, Supabase (server-only, service role), and pnpm on Node 24.

## Local setup

```bash
corepack enable          # provides the pinned pnpm version
pnpm install
cp .env.example .env.local
```

Fill in `.env.local`:

| Variable                    | Where to get it                                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------------------- |
| `SUPABASE_URL`              | Supabase → Project Settings → API                                                                       |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API Keys → `service_role` (secret)                                        |
| `APP_PASSWORD`              | Any password you like                                                                                   |
| `SESSION_SECRET`            | 32+ random characters: `node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"` |

The service role key bypasses Row Level Security. It is only ever read on the server, and must never be given a `NEXT_PUBLIC_` name.

```bash
pnpm dev                 # http://localhost:3000
```

### Sample data

```bash
pnpm seed                # ~40 "[Sample]" jobs; safe to re-run
pnpm seed:clean          # removes every sample job, its links and applications
```

> **Warning:** there is only one Supabase project, so local development and production share the same database. Sample jobs will show up in the deployed app as well. Run `pnpm seed:clean` once you're done testing.

### Commands

| Command                     | What it does                                                                            |
| --------------------------- | --------------------------------------------------------------------------------------- |
| `pnpm dev`                  | Development server                                                                      |
| `pnpm build` / `pnpm start` | Production build, then serve it on `$PORT` (default 3000)                               |
| `pnpm check`                | Lint, typecheck, format check and unit tests                                            |
| `pnpm test`                 | Unit tests (vitest)                                                                     |
| `pnpm format`               | Format with Prettier                                                                    |
| `pnpm db:types`             | Regenerate `src/lib/db/database.types.ts` from the live schema (needs `supabase login`) |

The build never needs database credentials.

## Deploying to Render

The repository includes a [`render.yaml`](render.yaml) Blueprint for one Node web service: region Singapore, Free plan, auto-deploy on every push to `main`, and health check at `/api/health`.

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint**, then select the repository. Render reads `render.yaml`.
3. When prompted, enter the four secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `APP_PASSWORD` and `SESSION_SECRET`.
4. Apply. The first deploy builds from `main`. After that, every push to `main` redeploys automatically.
5. Smoke test: `https://<service>.onrender.com/api/health` returns `{"ok":true}`, `/` redirects to the login page, and logging in shows the feed.

**Free plan:** the service spins down after about 15 minutes without traffic, so the first request afterwards takes roughly 30–60 seconds. To remove the delay, change `plan: free` to `plan: starter` in `render.yaml`.

**Don't add `corepack enable` to the build command.** Render's image already has pnpm, and its `/usr/bin` is read-only, so `corepack enable` fails with `EROFS`. If the build rejects the lockfile or the pnpm version, use `npx --yes pnpm@12.8.1 …` for the install and build, and `node_modules/.bin/next start` as the start command.

**Rollback:** revert the commit on `main`. Auto-deploy ships the previous version, and there are no database migrations to undo.

## Security notes

- Every route except `/login`, `/api/health` and `robots.txt` requires a session. The check happens in `src/proxy.ts`, and again in every page and Server Action.
- The session is an HMAC-signed, HttpOnly cookie that lasts 30 days. Changing `SESSION_SECRET` logs out every session.
- The app is never indexed: `robots.txt` disallows everything, and every page carries `noindex, nofollow`.
