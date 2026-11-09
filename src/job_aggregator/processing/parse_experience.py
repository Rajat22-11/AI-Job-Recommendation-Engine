"""Read a years-of-experience range from free text."""

from __future__ import annotations

import re

_RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?|y\b)", re.IGNORECASE)
_PLUS = re.compile(r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)", re.IGNORECASE)
_MINIMUM = re.compile(r"(?:min(?:imum)?\.?|at least)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", re.IGNORECASE)
_SINGLE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", re.IGNORECASE)
_FRESHER = re.compile(r"\b(fresher|freshers|entry[- ]level|no experience|0\s*years?)\b", re.IGNORECASE)


def parse_experience_range(text: str | None) -> tuple[float | None, float | None]:
    """Return (min, max) years, or (None, None) when the text states nothing usable."""
    if not text:
        return None, None
    if match := _RANGE.search(text):
        low, high = float(match.group(1)), float(match.group(2))
        return (low, high) if low <= high else (high, low)
    if match := _PLUS.search(text) or _MINIMUM.search(text):
        return float(match.group(1)), None
    if match := _SINGLE.search(text):
        value = float(match.group(1))
        if value <= 30:
            return value, value
    if _FRESHER.search(text):
        return 0.0, 0.0
    return None, None
