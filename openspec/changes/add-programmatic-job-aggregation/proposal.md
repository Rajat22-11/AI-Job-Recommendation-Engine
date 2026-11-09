# Proposal

## Why

The daily job aggregation currently runs as a Claude routine. Claude does the mechanical work (reading config, fetching, parsing, deduping, writing rows, notifying) and a session limit leaves most of it undone: on 2026-11-05 only 2 of 26 enabled sources were crawled, two SQL errors were fixed live, and LinkedIn was skipped because a connector was missing. Over the last 30 days only seven sources produced new jobs, and several stopped being crawled around 2026-10-20. Moving the deterministic work into code makes every run complete, repeatable, cheap and inspectable, and keeps Claude (or any LLM) out of the loop except where judgment is needed.

## What Changes

- Add a Python pipeline that performs fetch, parse, normalise, dedupe, score, persist and notify in code, writing to the existing Supabase "Jobs Recommendation Engine" database and leaving its schema and the read-only UI intact.
- Add one human-readable source registry file listing every website actively fetched and every LinkedIn influencer profile crawled, with enable flags and per-source fetch settings, so a developer can see at a glance what runs.
- Add a credential pool that accepts multiple tokens per service (for example Apify and Google Gemini from different accounts) and rotates to the next token when a rate limit or quota error occurs.
- Fetch jobs from open APIs and feeds (Jobcode, Himalayas, Remotive, RemoteOK, Greenhouse/Lever/Ashby company boards), from job boards through JobSpy (Indeed, Naukri, Glassdoor), and from LinkedIn influencer posts through Apify.
- Turn LinkedIn influencer posts that follow the "X IS HIRING" template into jobs: parse the labelled fields, resolve the `lnkd.in` link to the employer's apply URL, skip posts with no hiring marker or link, and never process the same post twice.
- Score fit with rules against `search_config`; an optional Gemini scorer is available behind configuration and off by default.
- Add run bookkeeping, health checks (a source returning zero or far below its baseline, no run in 24 hours) and a push notification through a configurable channel.
- Host the pipeline as a Render web service with a secured start endpoint. A scheduled GitHub Actions workflow in a private repository only calls that endpoint daily at an off-peak minute (retrying to tolerate a cold start, then polling status), and a second scheduled call runs the health check. Render's own cron is not used because it is not free. The start request returns a run id at once and the run continues in the background; overlapping runs are refused and the endpoint accepts any of several rotatable shared secrets. An optional local run on the user's PC (Windows Task Scheduler) is supported for sources that block datacenter IPs. A spike decides whether a free Render instance can finish the run; if not, the documented fallback runs the pipeline inside the GitHub Actions job.
- Retire the Claude routine only after the pipeline matches its coverage and the user confirms.
- Out of scope: UI changes, login-gated sources (Instahyre, Uplers, Upwork, WTTJ), Gmail job-alert parsing, Wellfound, Foundit, hiring.cafe, Adzuna, and any use of credentials or CAPTCHA solving. These can follow in later changes.

## Capabilities

### New Capabilities
- `source-registry`: the single configuration file that declares which websites and LinkedIn profiles are crawled, their fetch method and settings, and how it is validated and loaded.
- `credential-pool`: named services with multiple tokens each, selection, usage, and rotation on rate-limit or quota failure.
- `job-source-fetching`: retrieving raw job listings from each configured source type (open API or feed, JobSpy board, company ATS board) in a read-only, polite, failure-tolerant way and returning a common raw shape.
- `linkedin-post-ingestion`: collecting latest posts from configured LinkedIn profiles, recognising hiring posts, extracting job fields and the employer apply link, and tracking posts already seen.
- `job-persistence`: normalising raw jobs, applying the `company|title|location` dedupe key, and writing `jobs` and `job_sources` rows to Supabase without duplicates.
- `job-fit-scoring`: scoring each new job against `search_config` using rules, with an optional LLM scorer, and flagging internships and batch-restricted roles.
- `run-orchestration`: the daily run lifecycle, per-source status records, health checks, notifications and scheduled execution.

### Modified Capabilities

None. The project has no existing specs.

## Impact

- New Python project in this repository (source, config, tests, a small web service entry point, Render deployment config, GitHub Actions trigger workflows); there is no code today.
- Supabase: uses `sources`, `search_config`, `runs`, `source_runs`, `source_run_queries`, `jobs`, `job_sources`. Likely needs two small additions that the user must approve before they are applied to the live database: a default for `runs.run_id`, and a table for seen LinkedIn posts.
- New external services: Apify (free $5 monthly credit, roughly $1 a month expected), optionally Google Gemini (user supplies keys), a notification channel, Render (free web service; free hours and bandwidth limits are reported but unverified from Render's own documentation), GitHub Actions (private repository, only short trigger and polling jobs).
- New secrets: multiple Apify and Gemini tokens, Supabase service key, notification topic and the trigger secrets live in Render environment variables. GitHub holds only the trigger URL and one trigger secret. Nothing is committed.
- Terms and attribution: Himalayas, Remotive and RemoteOK require visible attribution and forbid passing jobs to other sites, so data stays private to the user's own UI.
- Known risks to settle by early spikes: whether a free Render instance can finish a background run before spinning down and how Render treats a background thread with no incoming requests, whether JobSpy works from Render's IP ranges, and whether the Apify LinkedIn actor returns full post text with the `lnkd.in` link intact.
- The existing Claude routine (`trig_01UkQ3i6Sk2WXPKLzHKy73m5`) keeps running until the user confirms the replacement is at parity.
