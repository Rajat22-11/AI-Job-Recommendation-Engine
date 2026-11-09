"""Jobcode (jobcode.in) through its public WordPress JSON posts endpoint.

Each post is an article with a "Particulars / Details" table (Company, Job Role, Job Location, ...)
and a button linking to the employer's apply page.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from job_aggregator.domain.models import FetchResult, RawListing, SearchConfig, SourceStatus
from job_aggregator.fetching.polite_http_client import PoliteHttpClient
from job_aggregator.registry.source_entry import SourceEntry

POSTS_PATH = "wp-json/wp/v2/posts"
PER_PAGE = 40
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_BUTTON_HREF = re.compile(
    r'<a[^>]*class="[^"]*wp-block-button__link[^"]*"[^>]*href="([^"]+)"'
    r'|<a[^>]*href="([^"]+)"[^>]*class="[^"]*wp-block-button__link',
    re.I,
)
_TAGS = re.compile(r"<[^>]+>")

LABELS = {
    "company": ("company", "company name", "organisation", "organization"),
    "role": ("job role", "role", "position", "designation", "job title"),
    "location": ("job location", "location", "locations"),
    "experience": ("experience", "experience required"),
    "salary": ("salary", "ctc", "package", "stipend"),
    "employment_type": ("job type", "employment type"),
    "work_mode": ("work mode",),
    "skills": ("required skills", "skills", "skills required", "programming skills", "technical skills"),
}

LastSuccessLookup = Callable[[str], datetime | None]


def _clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", fragment))).strip()


def parse_details_table(content_html: str) -> dict[str, str]:
    """Return the post's details table as {field: value} using the label aliases above."""
    found: dict[str, str] = {}
    for row in _ROW.findall(content_html):
        cells = [_clean(cell) for cell in _CELL.findall(row)]
        if len(cells) < 2:
            continue
        label = cells[0].lower().rstrip(":")
        for field_name, aliases in LABELS.items():
            if label in aliases and field_name not in found:
                found[field_name] = cells[1]
    return found


def find_apply_url(content_html: str) -> str | None:
    match = _BUTTON_HREF.search(content_html)
    if not match:
        return None
    return html.unescape(match.group(1) or match.group(2))


class JobcodeFetcher:
    def __init__(self, http: PoliteHttpClient, last_success_lookup: LastSuccessLookup,
                 now: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._http = http
        self._last_success = last_success_lookup
        self._now = now

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult:
        since = self._since(source)
        base = (source.base_url or "https://jobcode.in/").rstrip("/") + "/"
        params = {
            "per_page": PER_PAGE,
            "categories": ",".join(str(c) for c in source.setting("category_ids", [])),
            "categories_exclude": ",".join(str(c) for c in source.setting("excluded_category_ids", [])),
            "after": since.strftime("%Y-%m-%dT%H:%M:%S"),
            "_fields": "id,date,link,title,content",
        }
        params = {key: value for key, value in params.items() if value != ""}
        posts = []
        for page in range(1, int(source.setting("max_pages", 3)) + 1):
            batch = self._http.get_json(base + POSTS_PATH, source.id, {**params, "page": page})
            if not isinstance(batch, list) or not batch:
                break
            posts.extend(batch)
            if len(batch) < PER_PAGE:
                break

        listings, unparsed = [], 0
        for post in posts:
            listing = self._to_listing(post, source.id)
            if listing:
                listings.append(listing)
            else:
                unparsed += 1
        message = f"{len(posts)} posts since {since.date().isoformat()}"
        if unparsed:
            message += f"; {unparsed} without a details table or apply button"
        return FetchResult(source_id=source.id, status=SourceStatus.SUCCEEDED, listings=listings, message=message)

    def _since(self, source: SourceEntry) -> datetime:
        now = self._now()
        floor = now - timedelta(days=int(source.setting("lookback_days", 30)))
        last = self._last_success(source.id)
        return max(floor, last - timedelta(days=1)) if last else floor

    @staticmethod
    def _to_listing(post: dict, source_id: str) -> RawListing | None:
        content = (post.get("content") or {}).get("rendered", "")
        details = parse_details_table(content)
        apply_url = find_apply_url(content)
        if not details.get("company") or not details.get("role") or not apply_url:
            return None
        posted = post.get("date", "")[:10]
        work_mode = (details.get("work_mode") or "").lower()
        location = details.get("location")
        if work_mode == "remote" and location and "remote" not in location.lower():
            location = f"{location} (Remote)"
        return RawListing(
            source_id=source_id,
            title=details["role"],
            company=details["company"],
            apply_url=apply_url,
            source_url=post.get("link"),
            external_id=str(post.get("id")) if post.get("id") is not None else None,
            location=location,
            description=_clean(content)[:4000],
            salary_text=details.get("salary"),
            employment_type=details.get("employment_type"),
            experience_text=details.get("experience"),
            skills=[s.strip() for s in re.split(r",|/| or ", details.get("skills", "")) if s.strip()],
            posted_at=date.fromisoformat(posted) if posted else None,
            is_remote=True if work_mode == "remote" else None,
            apply_url_kind="employer",
        )
