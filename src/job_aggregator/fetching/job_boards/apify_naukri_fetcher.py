"""Naukri through an Apify actor, for when Naukri refuses direct requests (reCAPTCHA).

The actor (default `srd836/naukri-jobs-scraper`) runs on Apify's side; this code only sends a search
and reads the newest jobs back, a handful per search. Tokens come from the Apify credential pool and
rotate on quota errors. Output fields were confirmed with a live run on 2026-11-08.
"""

from __future__ import annotations

import math
from datetime import date

from job_aggregator.apify.run_actor import ActorRunner, run_apify_actor
from job_aggregator.credentials.credential_pool import CredentialPool, rotate_on_quota_error
from job_aggregator.domain.errors import AllTokensExhaustedError
from job_aggregator.domain.models import FetchResult, RawListing, SearchConfig, SourceStatus
from job_aggregator.fetching.job_boards.jobspy_board_fetcher import build_searches
from job_aggregator.registry.source_entry import SourceEntry

DEFAULT_ACTOR_ID = "srd836/naukri-jobs-scraper"
DEFAULT_MAX_SEARCHES = 6
DEFAULT_MAX_JOBS_PER_SEARCH = 10
DEFAULT_FRESHNESS_DAYS = 3


def _posted_date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def naukri_item_to_listing(item: dict, source_id: str) -> RawListing | None:
    """Map one actor item to the common shape; items without a title, company or link are dropped."""
    title, company, url = item.get("title"), item.get("company"), item.get("jobUrl")
    if not (title and company and url):
        return None
    locations = item.get("locations") or []
    work_mode = str(item.get("workMode") or "").lower()
    return RawListing(
        source_id=source_id, title=str(title), company=str(company), apply_url=str(url), source_url=str(url),
        external_id=str(item["jobId"]) if item.get("jobId") else None,
        location=", ".join(str(place) for place in locations) or None,
        description=item.get("jdSnippet"),
        salary_text=str(item["salary"]) if item.get("salary") else None,
        experience_text=str(item["experience"]) if item.get("experience") else None,
        skills=[str(skill) for skill in item.get("skills") or []],
        posted_at=_posted_date(item.get("postedDate")),
        is_remote=True if "remote" in work_mode else None,
        apply_url_kind="board",
    )


class ApifyNaukriFetcher:
    def __init__(self, pool: CredentialPool, runner: ActorRunner = run_apify_actor) -> None:
        self._pool = pool
        self._runner = runner

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult:
        actor_id = str(source.setting("actor_id", DEFAULT_ACTOR_ID))
        max_searches = int(source.setting("max_searches", DEFAULT_MAX_SEARCHES))
        max_jobs = int(source.setting("max_jobs_per_search", DEFAULT_MAX_JOBS_PER_SEARCH))
        freshness = int(source.setting("freshness_days", DEFAULT_FRESHNESS_DAYS))
        searches = build_searches(search_config, max_searches)
        listings: dict[str, RawListing] = {}
        errors: list[str] = []
        exhausted = False

        for term, location, _is_remote in searches:
            run_input = {"keywords": term, "location": location, "freshness": freshness, "maxJobs": max_jobs,
                         "experience": math.ceil(search_config.max_required_yoe)}
            try:
                items = rotate_on_quota_error(
                    self._pool, lambda token, run_input=run_input: self._runner(token, actor_id, run_input))
            except AllTokensExhaustedError as error:
                errors.append(str(error))
                exhausted = True
                break
            except Exception as error:  # noqa: BLE001 - one failed search must not lose the others
                errors.append(f"'{term}' in {location}: {type(error).__name__}: {str(error)[:150]}")
                continue
            for item in items:
                listing = naukri_item_to_listing(item, source.id)
                if listing:
                    listings.setdefault(listing.source_url or listing.apply_url, listing)

        message = f"{len(searches)} search(es) via Apify, {len(listings)} unique listings"
        if errors and not listings:
            status = SourceStatus.FAILED
        elif errors:
            status = SourceStatus.PARTIAL
        else:
            status = SourceStatus.SUCCEEDED
        if errors:
            message += f"; {len(errors)} problem(s): {errors[0]}"
        if exhausted:
            message += " (every Apify token is out of quota)"
        return FetchResult(source_id=source.id, status=status, listings=list(listings.values()), message=message)
