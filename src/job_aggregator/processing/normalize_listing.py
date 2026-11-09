"""Convert a raw listing into the `jobs` table fields."""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from job_aggregator.domain.models import NormalizedJob, RawListing, SearchConfig
from job_aggregator.processing.build_dedupe_key import build_dedupe_key
from job_aggregator.processing.parse_experience import parse_experience_range
from job_aggregator.processing.parse_salary import parse_salary_lpa
from job_aggregator.settings.app_settings import ProcessingSettings

_TAGS = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")
_INTERNATIONAL_REMOTE_WORDS = ("worldwide", "anywhere", "global", "international")
SUMMARY_MAX_CHARS = 600


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(word.lower())}(?!\w)", text) is not None


def plain_text(value: str | None) -> str:
    """Strip HTML tags and entities and collapse whitespace."""
    if not value:
        return ""
    return _WHITESPACE.sub(" ", html.unescape(_TAGS.sub(" ", value))).strip()


def is_remote_listing(listing: RawListing, settings: ProcessingSettings) -> bool:
    if listing.is_remote:
        return True
    location = (listing.location or "").lower()
    return any(_has_word(location, word) for word in settings.remote_location_words)


def classify_location_bucket(
    listing: RawListing, settings: ProcessingSettings, remote_bucket_override: str | None = None
) -> str:
    """Return one of the bucket values allowed by `jobs.location_bucket`."""
    location = (listing.location or "").lower()
    if is_remote_listing(listing, settings):
        if any(_has_word(location, word) for word in settings.india_words):
            return "remote_india"
        if any(_has_word(location, word) for word in _INTERNATIONAL_REMOTE_WORDS):
            return "remote_international"
        leftover = location
        for word in settings.remote_location_words:
            leftover = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", " ", leftover)
        if re.sub(r"[\W_]+", "", leftover):
            return "remote_international"
        return remote_bucket_override or settings.remote_without_country_bucket
    for bucket, words in settings.location_buckets.items():
        if any(_has_word(location, word) for word in words):
            return bucket
    return "other"


def classify_work_mode(listing: RawListing, settings: ProcessingSettings) -> str | None:
    if is_remote_listing(listing, settings):
        return "remote"
    text = f"{listing.location or ''} {listing.title}".lower()
    if any(_has_word(text, word) for word in settings.hybrid_location_words):
        return "hybrid"
    return "onsite" if listing.location else None


def classify_employment_type(listing: RawListing) -> str | None:
    text = f"{listing.employment_type or ''} {listing.title}".lower()
    if re.search(r"\bintern(ship)?\b", text):
        return "internship"
    if re.search(r"\b(contract|contractor|freelance|temporary)\b", text):
        return "contract"
    if re.search(r"\bpart[\s_-]?time\b", text):
        return "part_time"
    if re.search(r"\bfull[\s_-]?time\b|\bpermanent\b", text):
        return "full_time"
    return None


def classify_role_track(title: str, settings: ProcessingSettings) -> str:
    padded = f" {title.lower()} "
    for track, words in settings.role_tracks.items():
        if any(word.lower() in padded for word in words):
            return track
    return "other"


def classify_apply_url_kind(listing: RawListing, board_base_url: str) -> str:
    if listing.apply_url_kind in ("employer", "board"):
        return listing.apply_url_kind
    apply_host = urlparse(listing.apply_url).netloc.lower().removeprefix("www.")
    board_host = urlparse(board_base_url).netloc.lower().removeprefix("www.")
    if board_host and (apply_host == board_host or apply_host.endswith("." + board_host)):
        return "board"
    return "employer"


def normalize_skills(skills: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for skill in skills:
        cleaned = _WHITESPACE.sub(" ", skill).strip(" ,;.")
        if cleaned and cleaned.lower() not in seen:
            seen[cleaned.lower()] = cleaned
    return list(seen.values())


def normalize_listing(
    listing: RawListing,
    settings: ProcessingSettings,
    search_config: SearchConfig,
    board_base_url: str = "",
    remote_bucket_override: str | None = None,
) -> NormalizedJob:
    """Build a `NormalizedJob`. Fields that cannot be determined are left empty, never guessed."""
    description = plain_text(listing.description)
    experience_text = listing.experience_text or f"{listing.title} {description[:1500]}"
    min_yoe, max_yoe = parse_experience_range(experience_text)
    salary_min, salary_max = parse_salary_lpa(listing.salary_text, settings.usd_to_inr)
    salary_meets_min = None if salary_max is None else salary_max >= search_config.min_salary_lpa

    return NormalizedJob(
        dedupe_key=build_dedupe_key(listing.company, listing.title, listing.location,
                                    settings.known_cities, settings.remote_location_words),
        title=listing.title.strip(),
        company=listing.company.strip(),
        apply_url=listing.apply_url.strip(),
        location=(listing.location or "").strip() or None,
        location_bucket=classify_location_bucket(listing, settings, remote_bucket_override),
        work_mode=classify_work_mode(listing, settings),
        employment_type=classify_employment_type(listing),
        role_track=classify_role_track(listing.title, settings),
        min_yoe=min_yoe,
        max_yoe=max_yoe,
        salary_text=(listing.salary_text or "").strip() or None,
        salary_min_lpa=salary_min,
        salary_max_lpa=salary_max,
        salary_meets_min=salary_meets_min,
        skills=normalize_skills(listing.skills),
        summary=description[:SUMMARY_MAX_CHARS] or None,
        posted_at=listing.posted_at,
        apply_url_kind=classify_apply_url_kind(listing, board_base_url),
        source_id=listing.source_id,
        source_url=(listing.source_url or listing.apply_url).strip(),
        external_id=listing.external_id,
    )
