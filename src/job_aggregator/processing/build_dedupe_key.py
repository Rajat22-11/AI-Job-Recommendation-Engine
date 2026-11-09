"""Build the `company|title|location` key in the exact format already stored in `jobs.dedupe_key`.

Rules (inferred from live keys, see docs/database-notes.md):
- company: lowercased, whitespace collapsed, punctuation kept ("priceline.com").
- title: lowercased, "/" becomes a space, every other non-alphanumeric character removed, whitespace collapsed.
- location: "remote" when remote; else the earliest known city in the text; else the first part before , / |.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

_WHITESPACE = re.compile(r"\s+")
_TITLE_DROP = re.compile(r"[^\w\s]", re.UNICODE)
_LOCATION_SPLIT = re.compile(r"[,/|;()\-]")


def normalize_company_for_key(company: str) -> str:
    return _WHITESPACE.sub(" ", company.strip().lower())


def normalize_title_for_key(title: str) -> str:
    text = title.lower().replace("/", " ")
    text = _TITLE_DROP.sub("", text).replace("_", "")
    return _WHITESPACE.sub(" ", text).strip()


def normalize_location_for_key(
    location: str | None, known_cities: Sequence[str], remote_words: Sequence[str]
) -> str:
    if not location:
        return ""
    text = _WHITESPACE.sub(" ", location.lower())
    if any(_contains_word(text, word) for word in remote_words):
        return "remote"
    positions = [(match.start(), city) for city in known_cities if (match := _find_word(text, city))]
    if positions:
        earliest = min(position for position, _ in positions)
        # Prefer the longest city name starting at the earliest position ("navi mumbai" over "mumbai").
        return max((city for position, city in positions if position == earliest), key=len)
    first_part = _LOCATION_SPLIT.split(text)[0]
    return _WHITESPACE.sub(" ", re.sub(r"[^\w\s]", "", first_part)).strip()


def build_dedupe_key(
    company: str, title: str, location: str | None, known_cities: Sequence[str], remote_words: Sequence[str]
) -> str:
    return "|".join((
        normalize_company_for_key(company),
        normalize_title_for_key(title),
        normalize_location_for_key(location, known_cities, remote_words),
    ))


def _find_word(text: str, word: str) -> re.Match[str] | None:
    return re.search(rf"(?<!\w){re.escape(word.lower())}(?!\w)", text)


def _contains_word(text: str, word: str) -> bool:
    return _find_word(text, word) is not None
