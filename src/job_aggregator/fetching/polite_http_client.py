"""Shared HTTP access for fetchers: pacing per host, timeouts, bounded retries and block detection.

Read-only by design: only GET is exposed, and a login or challenge page stops the source instead of
being worked around.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import httpx

from job_aggregator.domain.errors import SourceBlockedError, SourceTimeoutError
from job_aggregator.settings.app_settings import FetchingSettings

logger = logging.getLogger(__name__)

TRANSIENT_STATUS = {429, 500, 502, 503, 504}
BLOCKED_STATUS = {401, 403, 407}
CHALLENGE_MARKERS = ("captcha", "verify you are human", "cf-challenge", "are you a robot", "unusual traffic")
LOGIN_URL_MARKERS = ("/login", "/signin", "/sign-in", "/authwall", "/uas/login")


class TransientFetchError(Exception):
    """A temporary failure that is worth retrying."""


class PoliteHttpClient:
    def __init__(
        self,
        settings: FetchingSettings,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: dict[str, float] = {}
        self._client = httpx.Client(
            timeout=settings.request_timeout_seconds,
            headers={"User-Agent": settings.user_agent, "Accept": "application/json, text/html;q=0.9"},
            follow_redirects=True,
            transport=transport,
        )

    def get_json(self, url: str, source_id: str, params: dict[str, Any] | None = None) -> Any:
        response = self.get(url, source_id, params)
        try:
            return response.json()
        except ValueError as exc:
            self._raise_if_blocked(response, source_id)
            raise TransientFetchError(f"{source_id}: response from {url} is not JSON") from exc

    def get_text(self, url: str, source_id: str, params: dict[str, Any] | None = None) -> str:
        return self.get(url, source_id, params).text

    def get(self, url: str, source_id: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """GET with pacing and bounded retries. Raises blocked, timeout or HTTP errors."""
        attempts = self._settings.max_retries + 1
        delay = self._settings.retry_backoff_seconds
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            self._wait_for_pacing(url)
            try:
                response = self._client.get(url, params=params)
            except httpx.TimeoutException as exc:
                last_error = SourceTimeoutError(source_id, self._settings.request_timeout_seconds)
                last_error.__cause__ = exc
            except httpx.TransportError as exc:
                last_error = TransientFetchError(f"{source_id}: network error {type(exc).__name__}")
            else:
                self._raise_if_blocked(response, source_id)
                if response.status_code in TRANSIENT_STATUS:
                    last_error = TransientFetchError(f"{source_id}: HTTP {response.status_code} from {url}")
                else:
                    response.raise_for_status()
                    return response
            if attempt < attempts:
                logger.info("%s: attempt %d/%d failed (%s); retrying", source_id, attempt, attempts, last_error)
                self._sleep(delay)
                delay *= 2
        assert last_error is not None
        raise last_error

    def close(self) -> None:
        self._client.close()

    def _wait_for_pacing(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_request_at.get(host)
        if last is not None:
            remaining = self._settings.pacing_seconds - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at[host] = self._clock()

    @staticmethod
    def _raise_if_blocked(response: httpx.Response, source_id: str) -> None:
        final_path = response.url.path.lower()
        if any(marker in final_path for marker in LOGIN_URL_MARKERS):
            raise SourceBlockedError(source_id, f"redirected to a login page ({response.url.host}{final_path})",
                                     kind="login")
        content_type = response.headers.get("content-type", "")
        body_start = response.text[:5000].lower() if "html" in content_type or not content_type else ""
        if any(marker in body_start for marker in CHALLENGE_MARKERS):
            raise SourceBlockedError(source_id, "challenge page (captcha or human verification)", kind="challenge")
        if response.status_code == 401:
            raise SourceBlockedError(source_id, "HTTP 401: sign-in required", kind="login")
        if response.status_code in BLOCKED_STATUS:
            raise SourceBlockedError(source_id, f"HTTP {response.status_code}", kind="ip")
