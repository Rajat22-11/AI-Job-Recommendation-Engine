# Migrations

Reviewable SQL files for the live Supabase database. **Nothing here is applied automatically.** Each file is applied by hand, in order, only after the owner approves it. Each file is written to be safe to run twice.

| File | What it does | Why |
|---|---|---|
| `001_runs_run_id_default.sql` | Default `gen_random_uuid()` on `runs.run_id` | The column has no default, which broke the old routine's first insert |
| `002_linkedin_seen_posts.sql` | Table `linkedin_seen_posts`, RLS on, no policies | Lets the pipeline skip LinkedIn posts it has already processed |

A unique index on `jobs.dedupe_key` is **not** needed: `jobs_dedupe_key_key` already exists (see `docs/database-notes.md`).
