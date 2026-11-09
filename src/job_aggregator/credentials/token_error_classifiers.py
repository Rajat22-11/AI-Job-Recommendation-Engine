"""Per-service rules deciding whether a failure means 'this token is spent or rejected'.

Apify's exact quota responses are not yet confirmed; the Apify rules below are a starting point to be
replaced with the real exhausted-token response captured during the Apify spike (tasks 17.2).
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum


class TokenFailure(str, Enum):
    QUOTA_EXHAUSTED = "quota exhausted"
    RATE_LIMITED = "rate limited"
    TOKEN_REJECTED = "token rejected"


TokenFailureClassifier = Callable[[BaseException], TokenFailure | None]


def _status_code(exc: BaseException) -> int | None:
    for attribute in ("status_code", "status", "code"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def _text(exc: BaseException) -> str:
    return f"{getattr(exc, 'type', '')} {exc}".lower()


def classify_apify_failure(exc: BaseException) -> TokenFailure | None:
    status, text = _status_code(exc), _text(exc)
    if status == 429 or "rate-limit" in text or "rate limit" in text:
        return TokenFailure.RATE_LIMITED
    if status == 402 or any(m in text for m in ("usage limit", "monthly usage", "insufficient", "not-enough-usage")):
        return TokenFailure.QUOTA_EXHAUSTED
    if status in (401, 403) and any(m in text for m in ("token", "auth", "unauthor", "forbidden")):
        return TokenFailure.TOKEN_REJECTED
    return None


def classify_gemini_failure(exc: BaseException) -> TokenFailure | None:
    status, text = _status_code(exc), _text(exc)
    if status == 429 or "resource_exhausted" in text or "quota" in text:
        return TokenFailure.QUOTA_EXHAUSTED if "quota" in text else TokenFailure.RATE_LIMITED
    if status in (401, 403) or "api_key_invalid" in text or "api key not valid" in text:
        return TokenFailure.TOKEN_REJECTED
    if status == 400 and "api key" in text:
        return TokenFailure.TOKEN_REJECTED
    return None


def classify_generic_failure(exc: BaseException) -> TokenFailure | None:
    status = _status_code(exc)
    if status == 429:
        return TokenFailure.RATE_LIMITED
    if status in (401, 402, 403):
        return TokenFailure.TOKEN_REJECTED
    return None


SERVICE_CLASSIFIERS: dict[str, TokenFailureClassifier] = {
    "apify": classify_apify_failure,
    "gemini": classify_gemini_failure,
}


def classifier_for_service(service: str) -> TokenFailureClassifier:
    """Return the service's classifier, or a conservative generic one."""
    return SERVICE_CLASSIFIERS.get(service, classify_generic_failure)
