# Source registry

`config/sources.yaml` lists **every** website and LinkedIn profile the pipeline crawls. If a target is not in this file, it is never fetched. The file is validated at the start of every run; a malformed file stops the run before anything is fetched, with an error naming the entry and the problem.

At the start of each run the registry is synchronised into the database `sources` table so run history and the UI stay consistent. The sync is deliberately narrow:

- A source that is **new** to the database is created from its registry entry.
- For a source that already exists, only `access_method` is kept in step with the registry (open API, company board, LinkedIn: `api`; job boards: `connector`; RSS: `rss`; public page: `public_scrape`). That makes the UI show "template not applicable" for sources that never use a URL template.
- **The UI owns the rest.** `enabled`, name, base URL and notes are never overwritten. If you disable a source in the UI, the next run does not fetch it, even though the registry file says `enabled: true`. The `enabled` flag in the file only sets the starting value for a source that is new to the database.

## Entry format

```yaml
sources:
  - id: himalayas            # required, unique, lowercase; becomes sources.id in the database
    name: Himalayas          # required, display name
    fetch_method: open_api   # required, one of the methods below
    enabled: true            # required, true or false
    base_url: https://himalayas.app   # optional, the site's home page
    provider: himalayas      # method-specific settings follow
    max_pages: 3
```

| `fetch_method` | Required settings | Optional settings |
|---|---|---|
| `open_api` | `provider`: `jobcode`, `himalayas`, `remotive`, `remoteok` or `workingnomads` | Jobcode: `category_ids`, `excluded_category_ids`, `lookback_days`, `max_pages`. Himalayas: `max_pages`, `max_keywords`, `country`. Remotive: `max_calls_per_day`, `category`, `limit` |
| `ats_board` | `provider`: `greenhouse`, `lever` or `ashby`; `companies`: list of board slugs | `location_words` (default `[india]`) |
| `rss_feed` | `provider`: `weworkremotely` | `feeds` (RSS URLs), `region_words` |
| `web_page` | `provider`: `arc` | `skill_pages`, `country_code` |
| `jobspy_board` | `site`: `indeed`, `naukri` or `glassdoor` | `max_searches` |
| `apify_job_board` | `provider`: `naukri` | `actor_id`, `max_searches`, `max_jobs_per_search`, `freshness_days` (needs `APIFY_TOKENS`) |
| `linkedin_profile_posts` | `profile_url` | `posts_per_run` (default from settings), `credential_service` (default `apify`) |

Rules enforced by the validator:
- `id`, `name`, `fetch_method` and `enabled` must be present; `enabled` must be `true` or `false`.
- Identifiers must be unique.
- `fetch_method` must be one of the seven above, and its required settings must be present.
- A source id may not appear in both `sources` and `not_fetched`.
- **No secrets.** Keys that look like `token`, `secret`, `password`, `api_key`, `cookie` or `session`, or values that look like real tokens, are rejected. Credentials are named by service only (for example `credential_service: apify`) and read from environment variables. See `docs/configuration.md`.

Search keywords, locations, experience limits and excluded companies are **not** in this file. They live in the `search_config` table, so changing a keyword needs no registry edit.

## Common changes

**Add a website** that uses an existing method. For example, a Greenhouse company:
1. Find its board slug: the part after `job-boards.greenhouse.io/` in the company's careers link.
2. Add the slug to the `companies` list of the `greenhouse` entry.
3. Check it with a dry run: `job-aggregator --dry-run --only-sources greenhouse`.

**Add a new ATS provider entry** (for example Lever):

```yaml
  - id: lever
    name: Lever
    base_url: https://jobs.lever.co
    fetch_method: ats_board
    provider: lever
    enabled: true
    companies: [some-company-slug]
```

**Sources the pipeline does not fetch:** a source enabled in the UI that has no registry entry is never fetched. List it under `not_fetched:` with a reason; each run then records it as skipped with that reason. A source in neither place is still recorded as skipped ("not in the source registry").

**Disable a target:** toggle it off in the UI (this wins), or set `enabled: false` here for a source not yet in the database. Keep the entry, so it stays documented and keeps its run history. The run does not fetch it and records no failure for it.

**Re-enable a target:** set `enabled: true`. No code change is needed; the next run fetches it.

**Add a LinkedIn profile:** see `docs/linkedin-profiles.md`.

**Add a brand-new fetch method:** this is a code change. Write a class implementing `JobFetcher` (`src/job_aggregator/fetching/job_fetcher.py`), add the method and its required settings to `FETCH_METHOD_REQUIRED_SETTINGS` (`registry/source_entry.py`), and add one entry to the builders table in `orchestration/build_pipeline.py`.

## Checking the file

```bash
python -m job_aggregator.registry.check_source_registry config/sources.yaml
```

This prints every entry with its enabled state, or the first validation error.
