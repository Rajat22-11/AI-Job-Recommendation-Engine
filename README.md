# Job Tracker UI

A personal, mobile-first web app for browsing aggregated job postings and tracking applications. It reads and writes the Supabase project **Jobs Recommendation Engine**, which a separate daily scraper (the "trigger") fills. The trigger only writes data. This repository owns the schema (see [Database migrations](#database-migrations)).

- **Feed** (`/`): active jobs with filters stored in the URL, one-tap Apply, and Save / Applied / Skip with Undo.
- **Job detail** (`/jobs/[id]`): every field, all source links, and an editable application record.
- **Tracker** (`/tracker`): applications grouped by status.
- **Sources** (`/sources`): enable or disable sources, see each source's search URL template state, last success, empty-run warnings, its latest runs, and which queries will resume on the next run. A banner appears on every page when a source needs you to log in.
- **Settings** (`/settings`): edit the search configuration, and add or edit sources.

### Adding a source

Enter only a name and the site's base URL (plus "Requires login" and notes if needed). The id is derived from the name, and the source is saved with access method _Auto-detect_ and no template. On its next run the trigger learns and checks a search URL template. Until then `/sources` shows **Waiting for first run**. The template then shows as:

| State                            | Meaning                                                                            |
| -------------------------------- | ---------------------------------------------------------------------------------- |
| Waiting for first run            | No template yet. The trigger will learn one.                                       |
| Will be verified on the next run | A template exists (manual, or after **Re-learn template**) and will be re-checked. |
| Verified (Learned / Manual)      | The trigger confirmed the template works. It is shown read-only.                   |
| Couldn't learn the template      | Learning failed. The trigger's reason is shown.                                    |
| Not applicable                   | Connector, API and RSS sources don't use URL templates.                            |

**Re-learn template** asks the trigger to re-check the current template on its next run. To set a template by hand, open the source in Settings → **Advanced override**. Clearing the template there has it learned from scratch. Saving a source's other fields never touches its template.

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

> If `pnpm db:types` fails (for example, not logged in), it writes the error into `database.types.ts`. Restore the file with `git checkout -- src/lib/db/database.types.ts`, then log in and run it again.

## Database migrations

Every schema change is a SQL file in [`supabase/migrations/`](supabase/migrations/), named `<version>_<name>.sql`, where the version matches the database's migration history. The first file is the baseline that created the schema. It has already been applied and is never re-run.

Rules for every migration, so it is safe while the trigger is running:

- **Additive and idempotent.** Use `add column if not exists`, `create table if not exists`, and `drop constraint if exists` followed by `add constraint … not valid` and `validate constraint`. Guard backfills with a `where` that matches nothing on a second run.
- **Never narrow** a value set or remove a column the trigger may write.
- **Lock down.** Every table has Row Level Security enabled and no policies, so only the service role can read or write it. Every view is `security_invoker = true`. A replaced view must restate that option and may only add columns at the end.
- **Fail fast.** Start with `set local lock_timeout = '5s';`, so a migration that meets a running trigger fails and can be retried instead of blocking it.

To apply one: dry-run the SQL inside `begin; … rollback;` in the Supabase SQL editor, then apply it as a migration (Supabase MCP `apply_migration` or `supabase db push`). Rename the file to the version recorded in the migration history, and run `pnpm db:types`.

## Deploying to Render

The repository includes a [`render.yaml`](render.yaml) Blueprint for one Node web service: region Singapore, Free plan, auto-deploy on every push to `main`, and health check at `/api/health`.

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint**, then select the repository. Render reads `render.yaml`.
3. When prompted, enter the four secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `APP_PASSWORD` and `SESSION_SECRET`.
4. Apply. The first deploy builds from `main`. After that, every push to `main` redeploys automatically.
5. Smoke test: `https://<service>.onrender.com/api/health` returns `{"ok":true}`, `/` redirects to the login page, and logging in shows the feed.

**Free plan:** the service spins down after about 15 minutes without traffic, so the first request afterwards takes roughly 30–60 seconds. To remove the delay, change `plan: free` to `plan: starter` in `render.yaml`.

**Don't add `corepack enable` to the build command.** Render's image already has pnpm, and its `/usr/bin` is read-only, so `corepack enable` fails with `EROFS`. If the build rejects the lockfile or the pnpm version, use `npx --yes pnpm@12.8.1 …` for the install and build, and `node_modules/.bin/next start` as the start command.

**Rollback:** revert the commit on `main`, and auto-deploy ships the previous version. Migrations are additive, so the database can stay as it is. Apply a migration before deploying code that needs it.

## Security notes

- Every route except `/login`, `/api/health` and `robots.txt` requires a session. The check happens in `src/proxy.ts`, and again in every page and Server Action.
- The session is an HMAC-signed, HttpOnly cookie that lasts 30 days. Changing `SESSION_SECRET` logs out every session.
- The app is never indexed: `robots.txt` disallows everything, and every page carries `noindex, nofollow`.
