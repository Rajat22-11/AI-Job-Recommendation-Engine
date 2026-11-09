# Sources: limits, attribution and how each is read

All access is read-only: GET requests to public endpoints, no logins, no form submissions, no CAPTCHA solving. A login wall or challenge page marks the source **blocked** for that run (`source_runs.status = needs_login` or `captcha`) and nothing more is attempted. Listings stay private to the owner's own database and UI; none are republished.

Shared behaviour (from `config/settings.yaml` → `fetching`): request timeout, bounded retries with doubling backoff on timeouts, network errors, 429 and 5xx; a minimum gap between requests to the same host; and a cap on listings per source per run.

## Open APIs and feeds

| Source | Endpoint | Calls per run | Limits and terms | Attribution kept |
|---|---|---|---|---|
| Jobcode | `jobcode.in/wp-json/wp/v2/posts` (WordPress) | 1 to `max_pages` (40 posts each) | Public WordPress API; posts newer than the last successful run minus one day, never older than `lookback_days` | Post URL as `job_sources.url`; apply URL is the employer's own link from the post's button |
| Himalayas | `himalayas.app/jobs/api/search?q=&country=India&page=` | `max_keywords` × up to `max_pages` | Public API, 20 results a page; paced by the shared gap | Original Himalayas job URL as `job_sources.url`, source name "Himalayas" |
| Remotive | `remotive.com/api/remote-jobs?category=software-dev` | 1, and none once `max_calls_per_day` (default 4) calls were made today across runs | Remotive asks for about 4 calls a day. **Jobs appear with a 24-hour delay.** Jobs must not be passed to other job sites | Remotive job URL as both apply and source URL, source name "Remotive" |
| Remote OK | `remoteok.com/api` | 1 | The first array element is a legal notice and is skipped. Requires a link back and naming Remote OK as the source | Remote OK job URL as both apply and source URL, source name "Remote OK" |
| Working Nomads | `workingnomads.com/jobsapi/_search?q=<keyword>` (the search its own site uses) | 1 per search keyword | robots.txt places no restriction | Working Nomads job page as `job_sources.url`, employer's own apply link, source named in the run message |

Keyword filtering: Remotive, Remote OK, We Work Remotely, Working Nomads, Arc and the company boards return broad lists, so listings are kept when the title (or tags) reach `matching.prefilter_min_ratio` for some search keyword. The keywords are search phrases such as "java spring boot developer": a keyword's ratio is the share of its significant words (the phrase without generic words like developer or engineer) that appear in the text. We Work Remotely uses the title only, because its category label is on every item of a feed. Himalayas searches each keyword directly. Jobcode posts are kept as they come (the categories already limit them).

## Feeds and public pages

| Source | Read from | Calls per run | Terms | Attribution kept |
|---|---|---|---|---|
| We Work Remotely | public RSS feeds listed under `feeds` in the registry (programming, back-end, full-stack) | 1 per feed | robots.txt allows these feeds. Only items whose region says anywhere, worldwide, global, Asia, APAC or India are kept, and the title must match a search keyword | Original We Work Remotely URL as both apply and source link |
| Arc | `arc.dev/remote-jobs/<skill>` for each `skill_pages` entry; the job list is embedded in the public page as JSON | 1 per skill page | robots.txt allows `/remote-jobs`. Jobs with no country restriction or listing India are kept | Arc URL as both apply and source link |

## Sources that are not fetched

Every other source enabled in the UI is listed under `not_fetched` in `config/sources.yaml` with the reason, observed on 2026-11-08. Each run records them as **skipped** with that reason, so the Sources page does not show stale results. Nothing below is bypassed: no logins, no challenges, no robots.txt exceptions.

| Source | Why not |
|---|---|
| Wellfound | Public pages sit behind a Cloudflare Turnstile challenge |
| Foundit | Answers automated requests with HTTP 403 Access Denied |
| Hiring Cafe | robots.txt disallows its search and paging URLs |
| Jobspresso | robots.txt disallows every URL with a query string, including its job feeds |
| Instahyre | Public pages carry no job data; matches need a signed-in session |
| Braintrust, Contra, Fiverr, Lemon.io, Toptal, Turing, Uplers, Upwork, Welcome to the Jungle | Login-gated or application-based; no public listings |
| FlexJobs | Paid membership (disabled in the UI) |

To fetch one of them later, write a fetcher only if the site allows it, add an entry to `sources:` and remove it from `not_fetched`.

## Company applicant-tracking boards

| Provider | Endpoint | Calls per run |
|---|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true` | 1 per company slug |
| Lever | `api.lever.co/v0/postings/{company}?mode=json` | 1 per company slug |
| Ashby | `api.ashbyhq.com/posting-api/job-board/{company}?includeCompensation=true` | 1 per company slug |

Each board lists all of a company's jobs worldwide. A job is kept when its location contains one of `location_words` (default `india`) or a `search_config.locations` entry, and its title matches a keyword. A board that returns 404 is skipped; the source is then recorded as **partial**, or **failed** if every board is missing. The apply URL is the employer's own (`apply_url_kind = employer`).

The Greenhouse slugs in `config/sources.yaml` were carried over from the old routine's `known_boards` list. All 11 fetched without error on 2026-11-08. Lever and Ashby are disabled until slugs are added.

## Naukri through Apify

Naukri answers direct requests with a reCAPTCHA (HTTP 406), so it is read by an Apify actor (`srd836/naukri-jobs-scraper`, set by `actor_id` in the registry). Each run sends at most `max_searches` (6) keyword and location searches, asking for the `max_jobs_per_search` (10) newest jobs posted within `freshness_days` (3) whose experience requirement fits `max_required_yoe`. The actor is a community actor, unaffiliated with Naukri; check its Apify page for current price and status. A live run on 2026-11-08 used no paid events. Tokens come from `APIFY_TOKENS` and rotate on quota errors; the Naukri apply link is the Naukri job page.

Glassdoor has no workable Apify route: one actor failed and the other ignored the India location and returned US jobs (tested 2026-11-08), so it stays on JobSpy and is currently blocked (HTTP 403).

## Job boards through JobSpy

Indeed and Glassdoor are read through the JobSpy library. These boards often refuse requests from cloud data-centre IP ranges, so they can be run from the owner's PC instead (see `docs/deployment.md`). A 403/429 or an empty result after a block is recorded as blocked rather than retried aggressively. Results are deduplicated against everything else, so running them from two places creates no duplicates.

## LinkedIn influencer posts

Read through the Apify actor named in `linkedin.apify_actor_id`, with no LinkedIn account or cookies, newest `posts_per_run` posts per profile, never more than `linkedin.max_posts_per_run` in total per run. `lnkd.in` short links are resolved by reading the public interstitial page. See `docs/linkedin-profiles.md`.
