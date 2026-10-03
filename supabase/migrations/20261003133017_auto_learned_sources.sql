-- auto_learned_sources
--
-- Schema for template learning, run tracking and query resumption by the daily
-- trigger. Schema changes are made only through migrations in this folder.
--
-- Rules for every migration here:
--   * additive and idempotent: re-running it changes nothing;
--   * never narrows a value set or removes a column the trigger may write;
--   * every table keeps RLS enabled with no policies (service role only);
--   * views keep security_invoker = true.
--
-- The lock timeout makes this fail fast instead of queueing behind a trigger
-- run that holds a conflicting lock; retry it in that case.

set local lock_timeout = '5s';
set local statement_timeout = '60s';

-- ===== sources: template learning state =====
alter table public.sources
  add column if not exists template_status        text default 'unverified',
  add column if not exists template_origin        text,
  add column if not exists template_verified_at   timestamptz,
  add column if not exists template_notes         text,
  add column if not exists consecutive_empty_runs int not null default 0,
  add column if not exists last_success_at        timestamptz,
  add column if not exists scrape_hints           jsonb not null default '{}'::jsonb;

-- New sources added from the app are saved as 'auto'; the trigger may also leave it empty.
alter table public.sources alter column access_method drop not null;
alter table public.sources alter column access_method set default 'auto';

alter table public.sources drop constraint if exists sources_access_method_check;
alter table public.sources add constraint sources_access_method_check
  check (access_method in ('auto','connector','public_scrape','browser_session','api','rss')) not valid;
alter table public.sources validate constraint sources_access_method_check;

alter table public.sources drop constraint if exists sources_template_status_check;
alter table public.sources add constraint sources_template_status_check
  check (template_status in ('unverified','verified','failed')) not valid;
alter table public.sources validate constraint sources_template_status_check;

alter table public.sources drop constraint if exists sources_template_origin_check;
alter table public.sources add constraint sources_template_origin_check
  check (template_origin in ('manual','auto')) not valid;
alter table public.sources validate constraint sources_template_origin_check;

-- Templates that existed before learning were written by hand and are in use.
update public.sources
   set template_origin = 'manual', template_status = 'verified'
 where search_url_template is not null and template_origin is null;

-- ===== source_runs: partial status and config snapshot =====
alter table public.source_runs
  add column if not exists config_snapshot jsonb;

alter table public.source_runs drop constraint if exists source_runs_status_check;
alter table public.source_runs add constraint source_runs_status_check
  check (status in ('ok','partial','needs_login','captcha','error','skipped')) not valid;
alter table public.source_runs validate constraint source_runs_status_check;

-- ===== runs: one row per trigger run =====
create table if not exists public.runs (
  run_id           uuid primary key,
  trigger_id       text,
  started_at       timestamptz default now(),
  finished_at      timestamptz,
  status           text,
  config_snapshot  jsonb,
  summary          text,
  notified         boolean default false
);
create index if not exists runs_started_idx on public.runs (started_at desc);
alter table public.runs enable row level security;

-- ===== source_run_queries: one row per search query, for resuming =====
-- run_id has no foreign key: query rows may be written without a runs row.
create table if not exists public.source_run_queries (
  id             uuid primary key default gen_random_uuid(),
  run_id         uuid not null,
  source_id      text not null references public.sources(id),
  keyword        text,
  location       text,
  url            text,
  page           int,
  status         text not null default 'pending',
  results_found  int,
  results_kept   int,
  error          text,
  created_at     timestamptz not null default now()
);
alter table public.source_run_queries drop constraint if exists source_run_queries_status_check;
alter table public.source_run_queries add constraint source_run_queries_status_check
  check (status in ('done','pending','rate_limited','failed','skipped')) not valid;
alter table public.source_run_queries validate constraint source_run_queries_status_check;
create index if not exists source_run_queries_source_run_idx
  on public.source_run_queries (source_id, run_id);
alter table public.source_run_queries enable row level security;

-- ===== jobs: where the apply link points =====
alter table public.jobs
  add column if not exists apply_url_kind text;

alter table public.jobs drop constraint if exists jobs_apply_url_kind_check;
alter table public.jobs add constraint jobs_apply_url_kind_check
  check (apply_url_kind in ('employer','board')) not valid;
alter table public.jobs validate constraint jobs_apply_url_kind_check;

update public.jobs set apply_url_kind = 'board' where apply_url_kind is null;

-- ===== job_feed: expose apply_url_kind =====
-- Columns are listed explicitly: a replaced view may only append columns, so
-- apply_url_kind goes last. security_invoker is restated so RLS stays in force.
create or replace view public.job_feed with (security_invoker = true) as
select j.id,
       j.dedupe_key,
       j.title,
       j.company,
       j.location,
       j.location_bucket,
       j.work_mode,
       j.employment_type,
       j.role_track,
       j.min_yoe,
       j.max_yoe,
       j.salary_text,
       j.salary_min_lpa,
       j.salary_max_lpa,
       j.salary_meets_min,
       j.skills,
       j.summary,
       j.apply_url,
       j.posted_at,
       j.fit_score,
       j.fit_reason,
       j.is_active,
       j.first_seen_at,
       j.last_seen_at,
       coalesce(a.status, 'new') as app_status,
       a.applied_on,
       a.notes as app_notes,
       a.resume_version,
       a.referral_contact,
       (select jsonb_agg(jsonb_build_object('source', s.source_id, 'url', s.url) order by s.scraped_at)
          from public.job_sources s where s.job_id = j.id) as links,
       j.apply_url_kind
from public.jobs j
left join public.applications a on a.job_id = j.id;
