-- Baseline: already applied to the "Jobs Recommendation Engine" project
-- (migration history version 20261002190056). Copied verbatim from
-- supabase_migrations.schema_migrations so the repository history matches the
-- database. Never re-run it.

-- ===== Config: job boards (add a row to add a website) =====
create table public.sources (
  id                  text primary key,                 -- slug, e.g. 'indeed'
  name                text not null,
  base_url            text not null,
  access_method       text not null check (access_method in ('connector','public_scrape','browser_session')),
  search_url_template text,                             -- placeholders: {query} {query_slug} {location}
  requires_login      boolean not null default false,
  enabled             boolean not null default true,
  notes               text,
  created_at          timestamptz not null default now()
);

-- ===== Config: search preferences (single row) =====
create table public.search_config (
  id                  smallint primary key default 1 check (id = 1),
  keywords            text[] not null,
  locations           text[] not null,
  min_salary_lpa      numeric(6,2) not null default 8.2,
  max_required_yoe    numeric(4,1) not null default 3,
  max_job_age_days    int not null default 30,
  excluded_companies  text[] not null default '{}',
  updated_at          timestamptz not null default now()
);

-- ===== Jobs (one row per real job, deduped across boards) =====
create table public.jobs (
  id                 uuid primary key default gen_random_uuid(),
  dedupe_key         text not null unique,              -- lower(company|title|city)
  title              text not null,
  company            text not null,
  location           text,
  location_bucket    text check (location_bucket in ('pune','mumbai','gujarat','remote_india','remote_international','other')),
  work_mode          text check (work_mode in ('onsite','hybrid','remote')),
  employment_type    text,
  role_track         text check (role_track in ('java_backend','ml_ai','data','full_stack','other')),
  min_yoe            numeric(4,1),
  max_yoe            numeric(4,1),
  salary_text        text,                              -- as shown on the posting
  salary_min_lpa     numeric(8,2),                      -- normalised annual INR lakhs
  salary_max_lpa     numeric(8,2),
  salary_meets_min   boolean,                           -- null = salary not disclosed
  skills             text[] not null default '{}',
  summary            text,
  apply_url          text not null,                     -- best direct link to apply
  posted_at          date,
  fit_score          smallint check (fit_score between 0 and 5),
  fit_reason         text,
  is_active          boolean not null default true,
  first_seen_at      timestamptz not null default now(),
  last_seen_at       timestamptz not null default now()
);
create index jobs_feed_idx on public.jobs (is_active, fit_score desc, posted_at desc);
create index jobs_bucket_idx on public.jobs (location_bucket);
create index jobs_track_idx on public.jobs (role_track);

-- ===== Every board link for a job =====
create table public.job_sources (
  id           uuid primary key default gen_random_uuid(),
  job_id       uuid not null references public.jobs(id) on delete cascade,
  source_id    text not null references public.sources(id),
  url          text not null unique,
  external_id  text,
  scraped_at   timestamptz not null default now()
);
create index job_sources_job_idx on public.job_sources (job_id);

-- ===== Application tracking (edited from the UI) =====
create table public.applications (
  job_id            uuid primary key references public.jobs(id) on delete cascade,
  status            text not null default 'saved'
                    check (status in ('saved','applied','interview','offer','rejected','skipped')),
  applied_on        date,
  resume_version    text,
  referral_contact  text,
  notes             text,
  updated_at        timestamptz not null default now()
);

-- ===== Per-source log of each daily run =====
create table public.source_runs (
  id             uuid primary key default gen_random_uuid(),
  run_id         uuid not null,
  source_id      text not null references public.sources(id),
  status         text not null check (status in ('ok','needs_login','captcha','error','skipped')),
  jobs_found     int not null default 0,
  jobs_new       int not null default 0,
  message        text,
  started_at     timestamptz not null default now(),
  finished_at    timestamptz
);
create index source_runs_recent_idx on public.source_runs (source_id, started_at desc);

-- ===== updated_at helper =====
create or replace function public.touch_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin new.updated_at = now(); return new; end; $$;

create trigger applications_touch before update on public.applications
  for each row execute function public.touch_updated_at();
create trigger search_config_touch before update on public.search_config
  for each row execute function public.touch_updated_at();

-- ===== Feed view for the UI =====
create view public.job_feed with (security_invoker = true) as
select j.*,
       coalesce(a.status, 'new') as app_status,
       a.applied_on, a.notes as app_notes, a.resume_version, a.referral_contact,
       (select jsonb_agg(jsonb_build_object('source', s.source_id, 'url', s.url) order by s.scraped_at)
          from public.job_sources s where s.job_id = j.id) as links
from public.jobs j
left join public.applications a on a.job_id = j.id;

-- ===== Lock down: no public access; UI server + trigger use the service role =====
alter table public.sources        enable row level security;
alter table public.search_config  enable row level security;
alter table public.jobs           enable row level security;
alter table public.job_sources    enable row level security;
alter table public.applications   enable row level security;
alter table public.source_runs    enable row level security;

-- ===== Seed config =====
insert into public.sources (id, name, base_url, access_method, search_url_template, requires_login, notes) values
 ('indeed',     'Indeed India',          'https://in.indeed.com',              'connector',       null, false,
  'Use the Indeed connector search_jobs with country_code IN; ~10 results per query, so run every keyword x location.'),
 ('himalayas',  'Himalayas',             'https://himalayas.app',              'public_scrape',
  'https://himalayas.app/jobs/countries/india/{query_slug}', false, 'Public listing pages; Plus/matches not needed.'),
 ('hiringcafe', 'Hiring Cafe',           'https://hiringcafe.com',             'public_scrape',
  'https://hiringcafe.com/classic?searchState={"searchQuery":"{query}","locations":[{"formatted_address":"India"}]}', false,
  'Location filter in URL is unreliable - filter by location after scraping. Postings show required YOE.'),
 ('wttj',       'Welcome to the Jungle', 'https://www.welcometothejungle.com', 'browser_session',
  'https://www.welcometothejungle.com/en/jobs-matches', true, 'Search is login-gated. Read via Claude in Chrome using Rajat''s session.'),
 ('uplers',     'Uplers',                'https://platform.uplers.com',        'browser_session',
  'https://platform.uplers.com/talent/all-opportunities', true, 'Login + reCAPTCHA. Read via Claude in Chrome using Rajat''s session.');

insert into public.search_config (keywords, locations, min_salary_lpa, max_required_yoe, max_job_age_days) values (
  array['java spring boot developer','java backend engineer','software engineer java','machine learning engineer',
        'AI engineer','data scientist','data engineer','full stack java react'],
  array['Pune','Mumbai','Ahmedabad','Gandhinagar GIFT City','Surat','Vadodara','Remote India','Remote International'],
  8.2, 3, 30);
