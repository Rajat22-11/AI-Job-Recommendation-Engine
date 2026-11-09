-- 002: remember every LinkedIn post the pipeline has processed, so a post is never processed twice.
-- Row-level security is enabled with no policy: only the service key (which bypasses RLS) can read or write.
-- Safe to run twice: every statement uses IF NOT EXISTS or is idempotent.
-- Applied to the live database on 2026-11-09.

-- Fails fast instead of queueing behind a running pipeline (same rule as the UI repo's migrations).
set local lock_timeout = '5s';
set local statement_timeout = '60s';

create table if not exists public.linkedin_seen_posts (
  post_url    text primary key,
  source_id   text not null references public.sources(id),
  outcome     text not null check (outcome in ('job_created', 'ignored', 'unparsed')),
  job_id      uuid references public.jobs(id) on delete set null,
  note        text,
  seen_at     timestamptz not null default now()
);

create index if not exists linkedin_seen_posts_source_idx
  on public.linkedin_seen_posts (source_id, seen_at desc);

alter table public.linkedin_seen_posts enable row level security;
