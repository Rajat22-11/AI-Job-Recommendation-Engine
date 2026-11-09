"""Ordered tokens per service with rotation on quota, rate-limit or rejected-token failures."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar

from job_aggregator.credentials.secret_redaction import redact_secrets, register_secret
from job_aggregator.credentials.token_error_classifiers import TokenFailureClassifier, classifier_for_service
from job_aggregator.domain.errors import AllTokensExhaustedError

logger = logging.getLogger(__name__)
T = TypeVar("T")


@dataclass
class CredentialPool:
    """Tokens for one service. A token marked unavailable is never used again in the same run."""

    service: str
    tokens: list[str]
    _unavailable: dict[int, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for position, token in enumerate(self.tokens, start=1):
            register_secret(token, f"{self.service} token #{position}")

    @property
    def size(self) -> int:
        return len(self.tokens)

    def available_positions(self) -> list[int]:
        """1-based positions of tokens still usable in this run, in configured order."""
        return [p for p in range(1, self.size + 1) if p not in self._unavailable]

    def first_available(self) -> tuple[int, str]:
        """Return the first usable token, or raise when none is left."""
        positions = self.available_positions()
        if not positions:
            raise AllTokensExhaustedError(self.service, self.size)
        position = positions[0]
        return position, self.tokens[position - 1]

    def mark_unavailable(self, position: int, reason: str) -> None:
        """Stop using the token at `position` for the rest of the run."""
        self._unavailable[position] = reason
        logger.warning("%s token #%d marked unavailable for this run: %s", self.service, position, reason)


def rotate_on_quota_error(
    pool: CredentialPool,
    call: Callable[[str], T],
    classifier: TokenFailureClassifier | None = None,
) -> T:
    """Run `call(token)`; on a token-related failure mark the token unavailable and retry with the next.

    Failures the classifier does not recognise as token-related are re-raised without rotating.
    """
    classify = classifier or classifier_for_service(pool.service)
    while True:
        position, token = pool.first_available()
        try:
            return call(token)
        except Exception as exc:  # noqa: BLE001 - classified below, re-raised when unrelated
            failure = classify(exc)
            if failure is None:
                raise
            pool.mark_unavailable(position, f"{failure.value}: {redact_secrets(str(exc))[:200]}")


def build_credential_pools(service_tokens: dict[str, list[str]]) -> dict[str, CredentialPool]:
    """Create one pool per service from the secrets read at start-up."""
    return {service: CredentialPool(service, list(tokens)) for service, tokens in service_tokens.items()}
