# Job aggregator

A daily pipeline that collects job openings for one person, scores how well each fits their search, and stores them in the Supabase "Jobs Recommendation Engine" database, where a read-only UI shows them. Every step is plain code: fetching, parsing, deduplicating, scoring, storing and notifying. It replaces a Claude routine that did this work by hand each day.

Sources:
- open APIs: Jobcode, Himalayas, Remotive, Remote OK;
- company job boards: Greenhouse, Lever, Ashby;
- Indeed, Naukri and Glassdoor through JobSpy;
- hiring posts from chosen LinkedIn creators, read through Apify.

Each run sends one phone notification through ntfy.sh.

It runs as a free Render web service, started each day by a GitHub Actions schedule. Optionally, the job boards also run from your own PC.

## Folder map

| Path | What it holds |
|---|---|
| `config/sources.yaml` | **Every website and LinkedIn profile crawled**, with on/off flags |
| `config/settings.yaml` | Behaviour settings: limits, retries, scoring, alerts, trigger waits |
| `src/job_aggregator/` | The code, one folder per concern (see `docs/architecture.md`) |
| `tests/` | Unit and contract tests; `tests/fixtures/` holds saved sample payloads |
| `migrations/` | Reviewable SQL, applied by hand only after approval |
| `scripts/` | GitHub trigger script, PC job-board run, Windows task registration |
| `.github/workflows/` | Daily trigger, health-check trigger, manual fallback |
| `render.yaml` | Render service definition (no secret values) |
| `docs/` | Architecture, configuration, sources, registry, LinkedIn, deployment, database notes |

## Set up and test

Python 3.11 or newer.

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"        # macOS/Linux: .venv/bin/pip
.venv/Scripts/python -m pytest               # run the tests (no network needed)
.venv/Scripts/ruff check src tests scripts   # lint
.venv/Scripts/python -m job_aggregator.registry.check_source_registry   # validate the source list
```

## Run it

```bash
# needs SUPABASE_URL and SUPABASE_SERVICE_KEY in the environment (plus APIFY_TOKENS for LinkedIn)
.venv/Scripts/job-aggregator --dry-run                 # fetch and score, print results, write nothing
.venv/Scripts/job-aggregator                           # the real run
.venv/Scripts/job-aggregator --check-health-only       # missed-run and stuck-source alerts
```

## Further reading

- `docs/architecture.md`: layers, run order, command line, service endpoints
- `docs/configuration.md`: every setting and secret
- `docs/source-registry.md`: adding, disabling and re-enabling sources
- `docs/linkedin-profiles.md`: adding an influencer and teaching the parser new wording
- `docs/sources.md`: each source's limits and attribution rules
- `docs/deployment.md`: Render, GitHub, the spike, the fallback, the PC run
- `docs/database-notes.md`: facts about the live schema the code relies on
