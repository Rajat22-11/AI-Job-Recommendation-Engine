"""Working Nomads (workingnomads.com) public job search endpoint, the one its own site uses.

robots.txt places no restriction. One request per search keyword. Each listing keeps the Working Nomads
job page as its source link and the employer's own apply link, and credits the source by name.
"""

from __future__ import annotations

from datetime import date

from job_aggregator.domain.models import FetchResult, RawListing, SearchConfig, SourceStatus
from job_aggregator.fetching.keyword_matching import DEFAULT_MATCHER, KeywordMatcher, matches_any_keyword
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.registry.source_entry import SourceEntry

SEARCH_URL = "https://www.workingnomads.com/jobsapi/_search"
JOB_PAGE = "https://www.workingnomads.com/jobs/{slug}"
OPEN_LOCATION_WORDS = ["anywhere", "worldwide", "global", "asia", "apac", "india", "remote"]


def locations_open_to_india(locations: list[str], words: list[str]) -> bool:
    if not locations:
        return True  # no restriction stated
    joined = " ".join(locations).lower()
    return any(word in joined for word in words)


def workingnomads_hit_to_listing(source_fields: dict, source_id: str) -> RawListing | None:
    slug = source_fields.get("slug")
    apply_url = source_fields.get("apply_url") or (JOB_PAGE.format(slug=slug) if slug else "")
    posted = (source_fields.get("pub_date") or "")[:10]
    locations = source_fields.get("locations") or []
    if source_fields.get("expired") or not apply_url:
        return None
    return RawListing(
        source_id=source_id, title=source_fields.get("title") or "", company=source_fields.get("company") or "",
        apply_url=apply_url, source_url=JOB_PAGE.format(slug=slug) if slug else apply_url,
        external_id=str(source_fields.get("id")) if source_fields.get("id") is not None else None,
        location="Remote (" + ", ".join(locations) + ")" if locations else "Remote",
        description=source_fields.get("description"), salary_text=source_fields.get("salary_range") or None,
        employment_type={"ft": "full_time", "pt": "part_time", "contract": "contract"}.get(
            source_fields.get("position_type") or "", None),
        experience_text=(source_fields.get("experience_level") or "").replace("_", " ").title() or None,
        skills=list(source_fields.get("tags") or [])[:8],
        posted_at=date.fromisoformat(posted) if posted else None, is_remote=True,
        apply_url_kind="employer" if source_fields.get("apply_url") else "board",
    )


class WorkingNomadsFetcher:
    def __init__(self, http: PoliteHttpClient, matcher: KeywordMatcher = DEFAULT_MATCHER) -> None:
        self._http = http
        self._matcher = matcher

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult:
        words = [w.lower() for w in source.setting("location_words", OPEN_LOCATION_WORDS)]
        size = int(source.setting("results_per_keyword", 50))
        listings: dict[str, RawListing] = {}
        calls = 0
        for keyword in search_config.keywords or [""]:
            payload = self._http.get_json(SEARCH_URL, source.id, {"q": keyword, "size": size})
            calls += 1
            hits = ((payload.get("hits") or {}).get("hits") or []) if isinstance(payload, dict) else []
            for hit in hits:
                fields = hit.get("_source") or {}
                if not locations_open_to_india(fields.get("locations") or [], words):
                    continue
                listing = workingnomads_hit_to_listing(fields, source.id)
                # The site's search matches any single word ("developer"), so keep only real keyword matches.
                if listing and matches_any_keyword([listing.title, " ".join(listing.skills)], search_config.keywords,
                                                   self._matcher):
                    listings.setdefault(listing.source_url, listing)
        return FetchResult(source_id=source.id, status=SourceStatus.SUCCEEDED, listings=list(listings.values()),
                           message=f"{calls} search call(s), {len(listings)} matching jobs open to India "
                                   "(source: Working Nomads)")
