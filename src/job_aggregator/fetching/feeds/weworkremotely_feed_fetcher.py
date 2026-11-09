"""We Work Remotely (weworkremotely.com) public RSS feeds. robots.txt allows these feeds.

Items look like: title "Company: Job title", region "Anywhere in the World", link, description (HTML).
Only jobs open to India are kept: the region says anywhere/worldwide/Asia/APAC/India. Each listing keeps
the original We Work Remotely link, which is also the apply link.
"""

from __future__ import annotations

from email.utils import parsedate_to_datetime

from defusedxml import ElementTree

from job_aggregator.domain.models import FetchResult, RawListing, SearchConfig, SourceStatus
from job_aggregator.fetching.keyword_matching import DEFAULT_MATCHER, KeywordMatcher, matches_any_keyword
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.registry.source_entry import SourceEntry

DEFAULT_FEEDS = ["https://weworkremotely.com/categories/remote-programming-jobs.rss"]
DEFAULT_REGION_WORDS = ["anywhere", "worldwide", "global", "asia", "apac", "india"]


def _text(item, tag: str) -> str:
    element = item.find(tag)
    return (element.text or "").strip() if element is not None and element.text else ""


def region_is_open(region: str, region_words: list[str]) -> bool:
    lower = region.lower()
    return any(word.lower() in lower for word in region_words)


def rss_item_to_listing(item, source_id: str) -> RawListing | None:
    raw_title = _text(item, "title")
    company, separator, title = raw_title.partition(": ")
    if not separator:
        company, title = "", raw_title
    link = _text(item, "link")
    published = _text(item, "pubDate")
    region = _text(item, "region")
    if not (company and title and link):
        return None
    try:
        posted = parsedate_to_datetime(published).date() if published else None
    except (TypeError, ValueError):
        posted = None
    return RawListing(
        source_id=source_id, title=title.strip(), company=company.strip(), apply_url=link, source_url=link,
        external_id=_text(item, "guid") or link, location=f"Remote ({region})" if region else "Remote",
        description=_text(item, "description"), employment_type=_text(item, "type") or None,
        skills=[c for c in [_text(item, "category")] if c], posted_at=posted, is_remote=True,
        apply_url_kind="board",
    )


class WeWorkRemotelyFeedFetcher:
    def __init__(self, http: PoliteHttpClient, matcher: KeywordMatcher = DEFAULT_MATCHER) -> None:
        self._http = http
        self._matcher = matcher

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult:
        feeds = source.setting("feeds", DEFAULT_FEEDS)
        region_words = source.setting("region_words", DEFAULT_REGION_WORDS)
        listings: dict[str, RawListing] = {}
        seen_items = 0
        for url in feeds:
            root = ElementTree.fromstring(self._http.get_text(url, source.id))
            for item in root.iter("item"):
                seen_items += 1
                listing = rss_item_to_listing(item, source.id)
                if not listing:
                    continue
                region = _text(item, "region")
                if region and not region_is_open(region, region_words):
                    continue
                # Title only: the category label ("Full-Stack Programming") is on every item of its feed.
                if matches_any_keyword([listing.title], search_config.keywords, self._matcher):
                    listings.setdefault(listing.source_url, listing)
        return FetchResult(source_id=source.id, status=SourceStatus.SUCCEEDED, listings=list(listings.values()),
                           message=f"{seen_items} feed items, {len(listings)} open to India and matching keywords")
