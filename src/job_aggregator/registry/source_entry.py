"""One validated registry entry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

FETCH_METHOD_REQUIRED_SETTINGS: dict[str, tuple[str, ...]] = {
    "open_api": ("provider",),
    "ats_board": ("provider", "companies"),
    "jobspy_board": ("site",),
    "apify_job_board": ("provider",),
    "linkedin_profile_posts": ("profile_url",),
    "rss_feed": ("provider",),
    "web_page": ("provider",),
}
"""Supported fetch methods and the settings each one needs. Adding a method starts here."""


@dataclass(frozen=True)
class SourceEntry:
    """A crawl target read from `config/sources.yaml`."""

    id: str
    name: str
    fetch_method: str
    enabled: bool
    base_url: str = ""
    settings: dict[str, Any] = field(default_factory=dict)

    def setting(self, key: str, default: Any = None) -> Any:
        """Return one method-specific setting, or `default` when absent."""
        return self.settings.get(key, default)
