# Deployment

```
GitHub Actions (private repo)                        Render web service (free plan)
  daily-job-run.yml  15:17 UTC                         job_aggregator.service
    POST /runs  ------- retry while asleep ------->    202 {run_id}  -> pipeline runs in a background thread
    GET /runs/{id} every 60 s until finished ----->    status (this traffic also keeps the instance awake)
  health-check.yml   03:43 UTC
    POST /health-check --------------------------->    missed-run and stuck-source check, ntfy alert

Owner's PC (optional)  Windows Task Scheduler 20:15 local
    scripts/run_job_boards_locally.ps1  -> CLI --only-methods jobspy_board -> same Supabase database
```

Secrets are split. Render holds every pipeline secret. GitHub holds only the trigger URL and one trigger secret. Render's own cron jobs are not used, because they are not free.

## 1. Private GitHub repository

1. Create a **private** repository and push this project. Schedules in public repositories are disabled after 60 days without activity, and a private repository also keeps the influencer list private.
2. Under **Settings → Secrets and variables → Actions → New repository secret**, add:
   - `TRIGGER_URL`: the Render service URL, for example `https://job-aggregator.onrender.com`. Add it after step 2.
   - `TRIGGER_SECRET`: one of the values you put in Render's `TRIGGER_SECRETS`.
3. Do **not** add pipeline secrets to GitHub unless you switch to the fallback (section 6).

## 2. Render web service

1. In Render: **New → Blueprint**, connect the GitHub repository. Render reads `render.yaml`: a free Python web service in Singapore, `pip install .`, started with `uvicorn job_aggregator.service.main:create_app_from_environment --factory`, health check `/healthz`.
2. Render asks for each `sync: false` variable. Set:

| Variable | Value |
|---|---|
| `SUPABASE_URL` | `https://ooqayggwtfhrqhsovbhd.supabase.co` |
| `SUPABASE_SERVICE_KEY` | the project's service-role key (Supabase → Project Settings → API) |
| `APIFY_TOKENS` | one or more Apify API tokens, comma-separated, first used first |
| `GEMINI_API_KEYS` | leave empty unless `scoring.gemini.enabled` is true |
| `NTFY_TOPIC` | a long random topic name; subscribe to it in the ntfy app |
| `TRIGGER_SECRETS` | one or more long random strings, comma-separated |
| `HEARTBEAT_URL` | optional, for example a healthchecks.io ping URL |
| `SKIP_FETCH_METHODS` | optional; `jobspy_board` if the job boards are fetched from your PC instead (section 7) |
| `SPIKE_FAKE_PIPELINE_MINUTES` | `12` during the spike (section 5), then delete it |

Generate a secret with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

3. After deploying, check `https://<service>.onrender.com/healthz` answers **204** with an empty body. A first request after idle can take a minute (cold start).

**Unverified free-plan limits.** The free plan reportedly gives 750 instance hours a month and spins down after about 15 minutes without requests. These figures come from third parties. Before relying on them, read the real limits in the Render dashboard (Workspace → Billing / Usage) and note them here.

## 3. Rotating the trigger secret (no downtime)

1. In Render, set `TRIGGER_SECRETS` to `old,new` and let it redeploy. Both secrets now work.
2. In GitHub, change `TRIGGER_SECRET` to `new`.
3. After the next successful daily run, set `TRIGGER_SECRETS` to `new` only.

## 4. Cold start, polling and failure

`scripts/trigger_and_wait.py` reads its limits from the `trigger` section of `config/settings.yaml`:

- **Start:** retries `POST /runs` every `start_retry_interval_seconds` for up to `start_wait_seconds` while Render wakes the instance (502/503/timeouts). A 401 fails at once.
- **Poll:** asks `GET /runs/{id}` every `poll_interval_seconds` until the run is `succeeded`, `partial`, `failed` or `interrupted`, or until `poll_limit_minutes`.
- **Fail visibly:** an unreachable service, a failed or interrupted run, or a run still going at the limit makes the workflow fail. GitHub then emails you. A `partial` run (a board blocked) passes with a warning.
- **One run at a time:** a second trigger while a run is active returns that run's id. A trigger after today's run finished returns the finished run, unless `trigger.repeat_trigger_behaviour` is `start_new`. To force a new run by hand: `POST /runs` with `{"force": true}`.
- **Restarts:** if Render restarts the instance mid-run, the run is reported as `interrupted` (never stuck as `running`) and the workflow fails.

Manual run from a terminal:

```bash
TRIGGER_URL=https://<service>.onrender.com TRIGGER_SECRET=<secret> python scripts/trigger_and_wait.py run
```

## 5. Render spike (do this before relying on the service)

Purpose: find out whether a free instance finishes a background run, and how it behaves with no incoming requests.

1. Set `SPIKE_FAKE_PIPELINE_MINUTES=12` in Render and redeploy. In this mode the pipeline only writes a `runs` row, then sleeps and logs `spike run ... alive: minute N` every minute.
2. **With polling:** run the `Daily job run (trigger)` workflow by hand. Record:
   - the cold-start time (the "retrying" lines);
   - whether the run reaches `succeeded` after about 12 minutes;
   - Render's logs for all 12 "alive" lines.
3. **Without polling:** wait 20 minutes with no traffic. Then start a run with a single `curl -X POST .../runs -H "Authorization: Bearer <secret>"` and send nothing else for 20 minutes. Afterwards, check the run's state and Render's logs. Did all 12 "alive" lines appear, or did the instance spin down mid-run?
4. Note the free plan's hours and bandwidth figures from the dashboard.
5. Record the numbers below, then delete `SPIKE_FAKE_PIPELINE_MINUTES`.

| Measurement | Result |
|---|---|
| Cold start (first request to answer) | not yet measured |
| 12-minute run with polling every 60 s | not yet measured |
| 12-minute run with no requests | not yet measured |
| Spin-down observed mid-run? when? | not yet measured |
| Free plan hours / bandwidth (from dashboard) | not yet read |
| Decision | pending: Render service, or fallback |

**Decision rule:** if the run completes with polling, keep the service; polling is part of the design. If it is cut off even with polling, switch to the fallback.

## 6. Switching to the fallback (pipeline inside GitHub Actions)

`fallback-pipeline-in-actions.yml` runs the same CLI inside the Actions job. It uses about 10 minutes of the roughly 2,000 free Linux minutes a month on a private repository.

1. Add the pipeline secrets as GitHub repository secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `APIFY_TOKENS`, `GEMINI_API_KEYS` (optional), `NTFY_TOPIC`, `HEARTBEAT_URL` (optional).
2. In `fallback-pipeline-in-actions.yml`, uncomment the `schedule:` block.
3. In `daily-job-run.yml`, delete the `schedule:` block. Keep `workflow_dispatch`.
4. For the health check, either keep the Render service running for `POST /health-check`, or add a step to the fallback workflow running `job-aggregator --check-health-only`.
5. Run the fallback once by hand with **Dry run** ticked, then once for real.

Both workflows share the `daily-job-run` concurrency group, so they never run at the same time.

## 7. Running the job boards from your PC (optional)

Indeed, Naukri and Glassdoor often block cloud IP ranges. Your PC's home connection is less likely to be blocked. Results go to the same database, and duplicates are impossible because jobs are keyed by `company|title|location`.

1. Install once: `python -m venv .venv` and `.venv\Scripts\pip install .`
2. Create `.env.local` in the project folder (git-ignored) with:
   ```
   SUPABASE_URL=https://ooqayggwtfhrqhsovbhd.supabase.co
   SUPABASE_SERVICE_KEY=...
   NTFY_TOPIC=...
   ```
3. Try it: `powershell -ExecutionPolicy Bypass -File scripts\run_job_boards_locally.ps1 -DryRun`. Logs go to `logs\`.
4. Schedule it daily: `powershell -ExecutionPolicy Bypass -File scripts\register_windows_task.ps1 -Time 20:15`. If the PC is asleep at that time, the task runs when it next wakes.
5. If the JobSpy spike (`docs/database-notes.md`) shows the boards are blocked from Render, set `SKIP_FETCH_METHODS=jobspy_board` in Render. The cloud run then leaves the job boards out, while the PC still fetches them. Keep them `enabled: true` in `config/sources.yaml`, because both environments read the same file.

## 8. Retiring the old Claude routine

Keep the Claude routine running alongside the new pipeline for several days. Compare per-source coverage in `source_runs`. Disable the routine only after you have explicitly approved parity.
