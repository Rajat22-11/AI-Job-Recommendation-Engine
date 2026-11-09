-- 001: give runs.run_id a default so a writer that forgets to supply one does not fail.
-- The pipeline always supplies its own UUID; this protects other writers.
-- Safe to run twice: SET DEFAULT simply replaces the default.
-- Applied to the live database on 2026-11-09.

-- Fails fast instead of queueing behind a running pipeline (same rule as the UI repo's migrations).
set local lock_timeout = '5s';
set local statement_timeout = '60s';

alter table public.runs
  alter column run_id set default gen_random_uuid();
