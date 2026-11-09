"""Bearer shared-secret check that accepts any of several secrets, so a secret can be rotated without downtime."""

from __future__ import annotations

import hmac


def extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def is_valid_secret(presented: str | None, accepted_secrets: list[str]) -> bool:
    """Constant-time comparison against every accepted secret (no early exit that would leak which matched)."""
    if not presented:
        return False
    presented_bytes = presented.encode("utf-8")
    matched = False
    for secret in accepted_secrets:
        matched |= hmac.compare_digest(presented_bytes, secret.encode("utf-8"))
    return matched
