"""Convert salary text to lakhs per annum (LPA)."""

from __future__ import annotations

import re

_NUMBER = r"(\d+(?:[.,]\d+)*)"
_RANGE_SEPARATOR = r"\s*(?:-|–|to)\s*(?:₹|rs\.?|inr|\$|usd)?\s*"
_LPA_RANGE = re.compile(_NUMBER + _RANGE_SEPARATOR + _NUMBER + r"\s*(?:lpa|l\b|lakhs?|lacs?)", re.IGNORECASE)
_LPA_SINGLE = re.compile(_NUMBER + r"\s*(?:lpa|l\b|lakhs?|lacs?)", re.IGNORECASE)
_CRORE = re.compile(_NUMBER + r"\s*(?:cr|crores?)\b", re.IGNORECASE)
_MONTHLY = re.compile(r"(per\s*month|/\s*month|/\s*mo\b|monthly|p\.?m\.?\b|stipend)", re.IGNORECASE)
_HOURLY = re.compile(r"(per\s*hour|/\s*h(ou)?r|hourly)", re.IGNORECASE)
_USD = re.compile(r"(\$|usd)", re.IGNORECASE)
_PLAIN_NUMBERS = re.compile(r"(?:₹|rs\.?|inr|\$|usd)?\s*" + _NUMBER + r"\s*(k\b)?", re.IGNORECASE)


def _to_float(token: str) -> float:
    return float(token.replace(",", ""))


def parse_salary_lpa(text: str | None, usd_to_inr: float) -> tuple[float | None, float | None]:
    """Return (min, max) in lakhs per annum, or (None, None) when no amount can be read."""
    if not text:
        return None, None
    months = 12 if _MONTHLY.search(text) else 1  # "1.2-1.5 lakh/month" is a monthly amount
    if match := _LPA_RANGE.search(text):
        return _ordered(_to_float(match.group(1)) * months, _to_float(match.group(2)) * months)
    if match := _LPA_SINGLE.search(text):
        value = round(_to_float(match.group(1)) * months, 2)
        return value, value
    if match := _CRORE.search(text):
        value = _to_float(match.group(1)) * 100
        return value, value

    amounts = []
    for match in _PLAIN_NUMBERS.finditer(text):
        raw = match.group(1)
        if not raw or not any(ch.isdigit() for ch in raw):
            continue
        value = _to_float(raw) * (1000 if match.group(2) else 1)
        if value > 0:
            amounts.append(value)
    if not amounts:
        return None, None
    amounts = amounts[:2]

    if _HOURLY.search(text):
        yearly = [a * 8 * 22 * 12 for a in amounts]
    elif _MONTHLY.search(text):
        yearly = [a * 12 for a in amounts]
    else:
        yearly = amounts
    if _USD.search(text):
        yearly = [a * usd_to_inr for a in yearly]
    lakhs = [round(a / 100_000, 2) for a in yearly]
    if max(lakhs) < 0.5:  # numbers too small to be a yearly amount in rupees; not a salary we can read
        return None, None
    return _ordered(min(lakhs), max(lakhs))


def _ordered(low: float, high: float) -> tuple[float, float]:
    low, high = round(low, 2), round(high, 2)
    return (low, high) if low <= high else (high, low)
