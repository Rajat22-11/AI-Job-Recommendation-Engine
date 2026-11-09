# Configuration

Three places hold configuration, each for one kind of thing:

| What | Where | Changed by |
|---|---|---|
| Which websites and LinkedIn profiles are crawled | `config/sources.yaml` (see `docs/source-registry.md`) | editing the file |
| How the pipeline behaves (limits, retries, thresholds, scoring, notifications, trigger waits) | `config/settings.yaml` (this page) | editing the file |
| What the owner is looking for (keywords, locations, salary, experience, excluded companies) | the `search_config` table in Supabase | editing the row |
| Secrets (tokens, keys, topic, trigger secrets) | environment variables (below) | Render dashboard, GitHub secrets, or `.env.local` on the PC |

`config/settings.yaml` is validated on load. An unknown key (for example a typo) or an invalid value stops the run with an error naming the key, such as `Invalid setting 'fetching.max_retires': unknown key`.

## Settings (`config/settings.yaml`)

### `fetching`: shared HTTP behaviour
| Key | Meaning |
|---|---|
| `request_timeout_seconds` | Time limit for one HTTP request |
| `max_retries` | Extra attempts after a temporary failure (timeout, network error, 429, 5xx) |
| `retry_backoff_seconds` | Wait before the first retry; doubles on each further retry |
| `pacing_seconds` | Minimum gap between two requests to the same host |
| `max_listings_per_source` | Listings kept per source per run; the rest are dropped and the message says so |
| `user_agent` | User-Agent header sent to open APIs |

### `matching`: how search keywords are applied
The keywords in `search_config` are search phrases ("java spring boot developer"), not text found in titles. A keyword's ratio is the share of its significant words (the phrase minus the generic words) found as whole words in the text.

| Key | Meaning |
|---|---|
| `generic_words` | Words ignored when measuring a ratio (developer, engineer, software, senior, ...) |
| `prefilter_min_ratio` | Ratio a title or tag must reach for a whole-feed source (Remotive, Remote OK, company boards) to keep a listing |
| `score_min_ratio` | Ratio the title, skills and summary must reach for the scorer to count a keyword match |

### `jobspy`: Indeed, Naukri, Glassdoor
| Key | Meaning |
|---|---|
| `country` | JobSpy `country_indeed` value (`india`) |
| `results_wanted` | Results requested per search |
| `hours_old` | Only jobs posted within this many hours |
| `max_searches_per_board` | Keyword × location searches per board per run, spread across all keywords and places; "Remote India" becomes a remote search in India and "Remote International" is skipped (a registry entry's `max_searches` overrides it) |

### `linkedin`: influencer posts
| Key | Meaning |
|---|---|
| `apify_actor_id` | Apify actor used to read profile posts |
| `max_posts_per_run` | Hard cap on posts fetched across all profiles in one run (keeps Apify cost bounded) |
| `default_posts_per_profile` | Posts per profile when an entry has no `posts_per_run` |
| `short_link_timeout_seconds` | Time limit for resolving one `lnkd.in` link |
| `hiring_markers` | Phrases that mark a hiring post (case-insensitive) |
| `field_aliases` | Label words per field: `company`, `role`, `experience`, `batch`, `location`, `skills`, `stipend`, `apply_link` |

### `processing`: normalisation
| Key | Meaning |
|---|---|
| `remote_location_words` | Words that make a location remote |
| `hybrid_location_words` | Words that make a job hybrid |
| `known_cities` | Cities recognised in a location; the first one found is the dedupe key's location |
| `location_buckets` | Words per bucket; only `pune`, `mumbai`, `gujarat` (plus the remote buckets) are allowed by the database |
| `india_words` | Words that make a remote job `remote_india` |
| `remote_without_country_bucket` | Bucket for a bare "Remote": `remote_india` or `remote_international` (an entry's `remote_bucket` overrides it) |
| `role_tracks` | Title words per track; only `java_backend`, `ml_ai`, `data`, `full_stack` are allowed (else `other`) |
| `usd_to_inr` | Rate used to convert USD salaries to lakhs per annum |

### `persistence`
| Key | Meaning |
|---|---|
| `stale_after_days_unseen` | A job not seen for this many days is marked inactive (rows are never deleted); `search_config.max_job_age_days` also retires old postings |

### `scoring`
| Key | Meaning |
|---|---|
| `weights` | Points added to a base of 3, then clamped to 1–5: `keyword_match`, `no_keyword_match`, `location_match`, `location_mismatch`, `experience_over_limit`, `salary_meets_min`, `salary_below_min`, `internship_or_batch`, `senior_title` (a title with one of `seniority_words` while the listing states no years of experience) |
| `internship_words` | Title words that mark an internship |
| `batch_pattern` | Regular expression that marks a role restricted to a graduating batch |
| `borderline_scores` | Scores the optional model may review |
| `gemini.enabled` | Turn the optional Gemini review on (off by default; needs `GEMINI_API_KEYS`) |
| `gemini.model` | Gemini model name |
| `gemini.max_jobs_per_run` | Most jobs reviewed by the model per run |
| `gemini.request_timeout_seconds` | Time limit for one model call |
| `gemini.min_seconds_between_calls` | Minimum gap between model calls. Bursts hit Gemini's per-minute limit (HTTP 429); 4.5 s stays under it |

The wording of the Gemini prompt is not in `settings.yaml`. It lives in **`config/gemini_prompt.yaml`**: `instruction` (sent as written; keep its JSON answer format) and `data_template` (the per-job text, with the placeholders `{criteria}`, `{job}`, `{rules_score}` and `{rules_reason}`, which must stay). Edit it and the next run uses the new wording; a broken file stops the run with a message naming the problem.

### `health`
| Key | Meaning |
|---|---|
| `consecutive_empty_runs_alert` | Alert when a source returns zero jobs this many runs in a row |
| `baseline_runs` | Recent runs averaged for a source's normal count |
| `low_ratio_alert` | Alert when a run returns less than this share of the average |
| `missed_run_hours` | Alert when no run has been recorded for this long |

### `notifications`
| Key | Meaning |
|---|---|
| `channel` | `ntfy` or `none` |
| `ntfy_server` | ntfy server URL; the topic is the secret `NTFY_TOPIC` |
| `top_matches_count` | Best new jobs listed in the run message |
| `min_score_for_top_match` | Lowest score listed as a top match |
| `heartbeat_enabled` | Ping `HEARTBEAT_URL` after a successful run |

### `trigger`: the hosted service and the GitHub workflows
| Key | Meaning |
|---|---|
| `start_wait_seconds` | How long the workflow keeps retrying to reach a sleeping service |
| `start_retry_interval_seconds` | Gap between those retries |
| `poll_interval_seconds` | Gap between status checks while a run is going (also keeps a free instance awake) |
| `poll_limit_minutes` | The workflow fails if the run has not finished by then |
| `repeat_trigger_behaviour` | After today's run finished: `return_finished` (default) or `start_new` |
| `schedule_hint` | Information only; the real schedule is the cron line in `.github/workflows/daily-job-run.yml` |
| `stale_running_minutes` | A run still marked running after this long is treated as interrupted |

## Secrets (environment variables)

Lists take several values separated by commas (semicolons or new lines also work). The first value is used first; the next is used when one hits a quota or rate limit. Values are never written to logs, notifications, database rows or responses. Logs name tokens by position only (`apify token #2`).

| Variable | Needed by | Where it lives |
|---|---|---|
| `SUPABASE_URL` | pipeline | Render; `.env.local` on the PC; GitHub only for the fallback |
| `SUPABASE_SERVICE_KEY` | pipeline | Render; `.env.local`; GitHub only for the fallback |
| `APIFY_TOKENS` | LinkedIn profiles (list) | Render; GitHub only for the fallback |
| `GEMINI_API_KEYS` | optional model scoring (list) | Render; GitHub only for the fallback |
| `NTFY_TOPIC` | notifications | Render; `.env.local`; GitHub only for the fallback |
| `HEARTBEAT_URL` | optional heartbeat | Render; GitHub only for the fallback |
| `TRIGGER_SECRETS` | the service's accepted secrets (list, for rotation) | **Render only** |
| `SKIP_FETCH_METHODS` | fetch methods the service leaves out (e.g. `jobspy_board`) | Render only, optional |
| `TRIGGER_URL` | the GitHub trigger workflows | **GitHub only** |
| `TRIGGER_SECRET` | the GitHub trigger workflows (one of `TRIGGER_SECRETS`) | **GitHub only** |
| `JOB_AGGREGATOR_CONFIG_DIR` | optional config folder for the service (default `config`) | Render, optional |
| `SPIKE_FAKE_PIPELINE_MINUTES` | Render spike only; remove afterwards | Render, temporary |

In normal operation GitHub holds only `TRIGGER_URL` and `TRIGGER_SECRET`.

### Running locally: one file for all tokens

Copy `.env.example` to `.env.local` in the project root (git-ignored) and fill it in. It uses the same variable names and the same comma-separated lists as Render, and `job-aggregator` (and the web service) read it at start-up:

```
copy .env.example .env.local
python -m job_aggregator.orchestration.run_daily --dry-run
```

A variable already set in the real environment wins over the file, so on Render (no file) nothing changes. Use `JOB_AGGREGATOR_ENV_FILE=path` to point at a different file. Only variable names are logged, never values.
