"""Reject listings that cannot be stored or that the owner excluded, counting each discard and its reason."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from job_aggregator.domain.models import RawListing

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


@dataclass
class ValidationOutcome:
    accepted: list[RawListing] = field(default_factory=list)
    discard_reasons: Counter = field(default_factory=Counter)

    def discard_count_for(self, source_id: str) -> int:
        return sum(count for (source, _), count in self.discard_reasons.items() if source == source_id)


def missing_required_field(listing: RawListing) -> str | None:
    """Return the name of the first empty required field, or None."""
    for field_name in ("title", "company", "apply_url"):
        if not (getattr(listing, field_name) or "").strip():
            return field_name
    if not listing.apply_url.strip().lower().startswith(("http://", "https://")):
        return "apply_url"
    return None


def is_excluded_company(company: str, excluded_companies: list[str]) -> bool:
    """True when an excluded name appears as a whole word sequence in the company name."""
    normalized = f" {_NON_ALNUM.sub(' ', company.lower()).strip()} "
    for excluded in excluded_companies:
        token = _NON_ALNUM.sub(" ", excluded.lower()).strip()
        if token and f" {token} " in normalized:
            return True
    return False


def validate_listings(listings: list[RawListing], excluded_companies: list[str]) -> ValidationOutcome:
    """Keep valid, non-excluded listings; count every discard by (source, reason)."""
    outcome = ValidationOutcome()
    for listing in listings:
        missing = missing_required_field(listing)
        if missing:
            outcome.discard_reasons[(listing.source_id, f"missing {missing}")] += 1
        elif is_excluded_company(listing.company, excluded_companies):
            outcome.discard_reasons[(listing.source_id, "excluded company")] += 1
        else:
            outcome.accepted.append(listing)
    return outcome
