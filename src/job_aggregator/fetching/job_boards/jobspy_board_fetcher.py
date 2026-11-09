"""Indeed, Naukri and Glassdoor through the JobSpy library (python-jobspy).

These boards often refuse cloud data-centre IPs. JobSpy usually logs a 403/429 instead of raising, so
this fetcher watches JobSpy's log messages as well as exceptions. A block is recorded, never bypassed.
"""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from job_aggregator.domain.models import FetchResult, RawListing, SearchConfig, SourceStatus
from job_aggregator.registry.source_entry import SourceEntry
from job_aggregator.settings.app_settings import JobSpySettings

BLOCK_MARKERS = re.compile(r"\b(403|429)\b|blocked|captcha|forbidden|too many requests|rate limit", re.IGNORECASE)
CHALLENGE_WORDS = re.compile(r"captcha|verify you are human|human verification", re.IGNORECASE)
INTERVAL_WORDS = {"yearly": "per year", "monthly": "per month", "weekly": "per week", "daily": "per day",
                  "hourly": "per hour"}

ScrapeJobs = Callable[..., Any]


def _default_scrape_jobs(**kwargs: Any) -> Any:
    from jobspy import scrape_jobs  # imported lazily: heavy (pandas) and only needed when this source runs

    return scrape_jobs(**kwargs)


def _value(row: dict, key: str) -> Any:
    value = row.get(key)
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if str(value) in ("nan", "NaT", "<NA>", "None", ""):
        return None
    return value


def jobspy_salary_text(row: dict) -> str | None:
    low, high = _value(row, "min_amount"), _value(row, "max_amount")
    if low is None and high is None:
        return None
    currency = _value(row, "currency") or ""
    amounts = " - ".join(f"{float(v):,.0f}" for v in (low, high) if v is not None)
    interval = INTERVAL_WORDS.get(str(_value(row, "interval") or "yearly").lower(), "per year")
    return f"{currency} {amounts} {interval}".strip()


def _posted_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def jobspy_row_to_listing(row: dict, source_id: str) -> RawListing:
    skills = _value(row, "skills")
    job_type = _value(row, "job_type")
    return RawListing(
        source_id=source_id,
        title=str(_value(row, "title") or ""),
        company=str(_value(row, "company") or ""),
        apply_url=str(_value(row, "job_url_direct") or _value(row, "job_url") or ""),
        source_url=_value(row, "job_url"),
        external_id=_value(row, "id"),
        location=_value(row, "location"),
        description=_value(row, "description"),
        salary_text=jobspy_salary_text(row),
        employment_type=str(job_type) if job_type else None,
        experience_text=_value(row, "experience_range"),
        skills=[s.strip() for s in str(skills).split(",") if s.strip()] if skills else [],
        posted_at=_posted_date(_value(row, "date_posted")),
        is_remote=bool(_value(row, "is_remote")) or None,
        apply_url_kind="employer" if _value(row, "job_url_direct") else "board",
    )


class _BlockLogCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.block_messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if BLOCK_MARKERS.search(message):
            self.block_messages.append(message[:200])


def _board_locations(locations: list[str]) -> list[tuple[str, bool]]:
    """(location sent to the board, remote flag). Remote entries come first.

    "Remote India" (or "Remote") becomes a remote search within India. "Remote International" cannot be
    searched on India boards and is left out here.
    """
    remote: list[tuple[str, bool]] = []
    onsite: list[tuple[str, bool]] = []
    for location in locations:
        lower = location.strip().lower()
        if lower.startswith("remote"):
            if "international" not in lower and ("India", True) not in remote:
                remote.append(("India", True))
        elif lower:
            onsite.append((location.strip(), False))
    return (remote + onsite) or [("India", False)]


def build_searches(search_config: SearchConfig, max_searches: int) -> list[tuple[str, str, bool]]:
    """(search term, location, remote flag), spread across both keywords and locations, capped.

    Taking the i-th keyword with the i-th location (each wrapping around) gives distinct pairs, so a small
    cap still touches many keywords and places, instead of one keyword across every place.
    """
    keywords = search_config.keywords or [""]
    locations = _board_locations(search_config.locations)
    combos = []
    for shift in range(len(locations)):          # every keyword/location pair appears exactly once
        for i, keyword in enumerate(keywords):
            location, is_remote = locations[(i + shift) % len(locations)]
            combos.append((keyword, location, is_remote))
    return combos[:max_searches]


class JobSpyBoardFetcher:
    def __init__(self, settings: JobSpySettings, scrape_jobs: ScrapeJobs = _default_scrape_jobs) -> None:
        self._settings = settings
        self._scrape_jobs = scrape_jobs

    def fetch(self, source: SourceEntry, search_config: SearchConfig) -> FetchResult:
        site = source.setting("site")
        max_searches = int(source.setting("max_searches", self._settings.max_searches_per_board))
        searches = build_searches(search_config, max_searches)
        listings: dict[str, RawListing] = {}
        blocked: list[str] = []
        errors: list[str] = []
        collector = _BlockLogCollector()
        # JobSpy logs per site as "JobSpy:<Site>" with propagation off, so attach to the site's own logger.
        watched_loggers = [logging.getLogger(name) for name in ("JobSpy", f"JobSpy:{str(site).capitalize()}")]
        for watched in watched_loggers:
            watched.addHandler(collector)
        try:
            for term, location, is_remote in searches:
                try:
                    frame = self._scrape_jobs(
                        site_name=[site], search_term=term, location=location, is_remote=is_remote,
                        results_wanted=self._settings.results_wanted, hours_old=self._settings.hours_old,
                        country_indeed=self._settings.country, description_format="markdown", verbose=1,
                    )
                except Exception as exc:  # noqa: BLE001 - classified as blocked or failed below
                    message = f"{type(exc).__name__}: {exc}"[:200]
                    (blocked if BLOCK_MARKERS.search(message) else errors).append(f"'{term}' in {location}: {message}")
                    if blocked:
                        break  # stop hammering a board that refuses us
                    continue
                rows = frame.to_dict("records") if hasattr(frame, "to_dict") else list(frame or [])
                for row in rows:
                    listing = jobspy_row_to_listing(row, source.id)
                    listings.setdefault(listing.source_url or listing.apply_url, listing)
                if collector.block_messages:
                    blocked.extend(collector.block_messages)
                    break
        finally:
            for watched in watched_loggers:
                watched.removeHandler(collector)

        message = f"{len(searches)} search(es) planned on {site}, {len(listings)} unique listings"
        if blocked:
            status = SourceStatus.PARTIAL if listings else SourceStatus.BLOCKED
            message += f"; blocked: {blocked[0]}"
        elif errors and not listings:
            status = SourceStatus.FAILED
            message += f"; errors: {errors[0]}"
        elif errors:
            status = SourceStatus.PARTIAL
            message += f"; {len(errors)} search(es) failed: {errors[0]}"
        else:
            status = SourceStatus.SUCCEEDED
        block_kind = None
        if blocked:
            block_kind = "challenge" if CHALLENGE_WORDS.search(" ".join(blocked)) else "ip"
        return FetchResult(source_id=source.id, status=status, listings=list(listings.values()), message=message,
                           block_kind=block_kind)
