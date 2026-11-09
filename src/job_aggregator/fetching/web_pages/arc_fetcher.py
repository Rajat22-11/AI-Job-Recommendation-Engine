"""Arc (arc.dev) public remote-jobs pages. robots.txt allows /remote-jobs.

Each skill page ("https://arc.dev/remote-jobs/java") is server-rendered with its job list embedded as
JSON in the page (`__NEXT_DATA__`): Arc's own contract jobs and jobs from employers' boards. Only reads
the public page. Jobs are kept when open to India (no country restriction, or India listed).
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from job_aggregator.domain.models import FetchResult, RawListing, SearchConfig, SourceStatus
from job_aggregator.fetching.keyword_matching import DEFAULT_MATCHER, KeywordMatcher, matches_any_keyword
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.registry.source_entry import SourceEntry

PAGE_URL = "https://arc.dev/remote-jobs/{skill}"
ARC_JOB_URL = "https://arc.dev/remote-jobs/details/{slug}-{key}"
EXTERNAL_JOB_URL = "https://arc.dev/remote-jobs/j/{slug}-{key}"
_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def page_job_lists(page_html: str) -> tuple[list[dict], list[dict]]:
    """(Arc's own jobs, external jobs) embedded in a skill page; empty when the page has none."""
    match = _NEXT_DATA.search(page_html)
    if not match:
        return [], []
    props = json.loads(match.group(1)).get("props", {}).get("pageProps", {})
    return list(props.get("arcJobs") or []), list(props.get("externalJobs") or [])


def open_to_india(job: dict, country_code: str) -> bool:
    countries = job.get("requiredCountries") or []
    return not countries or country_code in countries


def _posted(job: dict):
    stamp = job.get("postedAt")
    return datetime.fromtimestamp(stamp, UTC).date() if isinstance(stamp, int | float) else None


def arc_job_to_listing(job: dict, source_id: str, is_arc_job: bool) -> RawListing | None:
    slug, key = job.get("urlString"), job.get("randomKey")
    company = (job.get("company") or {}).get("name") or ("Arc" if is_arc_job else "")
    if not (slug and key and job.get("title")):
        return None
    url = (ARC_JOB_URL if is_arc_job else EXTERNAL_JOB_URL).format(slug=slug, key=key)
    low, high = job.get("minAnnualSalary"), job.get("maxAnnualSalary")
    salary = f"USD {low:,} - {high:,} per year" if low and high else None
    return RawListing(
        source_id=source_id, title=job["title"], company=company, apply_url=url, source_url=url, external_id=key,
        location="Remote (Worldwide)" if not job.get("requiredCountries") else "Remote (India)",
        salary_text=salary,
        employment_type="contract" if job.get("jobType") == "contract" else "full_time",
        experience_text=" ".join(job.get("experienceLevels") or [job.get("experienceLevel") or ""]).strip() or None,
        skills=[c.get("name") for c in job.get("categories") or [] if c.get("name")][:8],
        posted_at=_posted(job), is_remote=True, apply_url_kind="board",
    )


class ArcFetcher:
    def __init__(self, http: PoliteHttpClient, matcher: KeywordMatcher = DEFAULT_MATCHER) -> None:
        self._http = http
        self._matcher = matcher

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult:
        skills = source.setting("skill_pages", ["java", "python", "machine-learning", "react"])
        country = source.setting("country_code", "IN")
        listings: dict[str, RawListing] = {}
        seen = 0
        for skill in skills:
            arc_jobs, external_jobs = page_job_lists(self._http.get_text(PAGE_URL.format(skill=skill), source.id))
            for is_arc_job, jobs in ((True, arc_jobs), (False, external_jobs)):
                for job in jobs:
                    seen += 1
                    if not open_to_india(job, country):
                        continue
                    listing = arc_job_to_listing(job, source.id, is_arc_job)
                    if listing and matches_any_keyword([listing.title, " ".join(listing.skills)],
                                                       search_config.keywords, self._matcher):
                        listings.setdefault(listing.source_url, listing)
        return FetchResult(source_id=source.id, status=SourceStatus.SUCCEEDED, listings=list(listings.values()),
                           message=f"{len(skills)} skill page(s), {seen} jobs seen, {len(listings)} open to India "
                                   "and matching keywords")
