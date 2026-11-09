"""Resolve an `lnkd.in` short link to the employer's URL by reading LinkedIn's public interstitial page.

The page answers 200 (no redirect) and carries the destination on the anchor marked
`data-tracking-control-name="external_url_click"`. If that is missing, the first link that is not a
LinkedIn domain is used. On any failure the original short link is kept and flagged unresolved.
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_EXTERNAL_ANCHOR = re.compile(
    r'<a[^>]*data-tracking-control-name="external_url_click"[^>]*href="([^"]+)"'
    r'|<a[^>]*href="([^"]+)"[^>]*data-tracking-control-name="external_url_click"',
    re.IGNORECASE,
)
_ANCHOR_HREF = re.compile(r'<a[^>]*href="(https?://[^"]+)"', re.IGNORECASE)
LINKEDIN_HOSTS = ("linkedin.com", "licdn.com", "lnkd.in")
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"


@dataclass(frozen=True)
class ResolvedLink:
    url: str
    resolved: bool


def is_short_link(url: str) -> bool:
    return urlparse(url).netloc.lower().removeprefix("www.") == "lnkd.in"


def _is_linkedin_host(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == h or host.endswith("." + h) for h in LINKEDIN_HOSTS)


def destination_from_interstitial(page_html: str) -> str | None:
    """Return the destination URL named by an `lnkd.in` page, or None."""
    if match := _EXTERNAL_ANCHOR.search(page_html):
        return html.unescape(match.group(1) or match.group(2))
    for href in _ANCHOR_HREF.findall(page_html):
        if not _is_linkedin_host(href):
            return html.unescape(href)
    return None


def resolve_short_link(url: str, client: httpx.Client | None = None, timeout_seconds: float = 15) -> ResolvedLink:
    """Resolve `url` if it is an `lnkd.in` link; any other URL is returned unchanged as resolved."""
    if not is_short_link(url):
        return ResolvedLink(url, resolved=True)
    owns_client = client is None
    client = client or httpx.Client(timeout=timeout_seconds, headers={"User-Agent": BROWSER_USER_AGENT})
    try:
        response = client.get(url, follow_redirects=False)
        if response.is_redirect and response.headers.get("location"):
            location = response.headers["location"]
            if not _is_linkedin_host(location):
                return ResolvedLink(location, resolved=True)
        destination = destination_from_interstitial(response.text) if response.status_code == 200 else None
        if destination:
            return ResolvedLink(destination, resolved=True)
        logger.info("could not read destination of %s (HTTP %s)", url, response.status_code)
    except httpx.HTTPError as exc:
        logger.info("could not resolve %s: %s", url, type(exc).__name__)
    finally:
        if owns_client:
            client.close()
    return ResolvedLink(url, resolved=False)
