"""Error types. Each message names the registry entry, source or service involved."""

from __future__ import annotations


class JobAggregatorError(Exception):
    """Base class for every error raised by this package."""


class InvalidRegistryError(JobAggregatorError):
    """The source registry file is malformed; the run stops before any fetch."""

    def __init__(self, entry_id: str | None, reason: str) -> None:
        self.entry_id = entry_id
        self.reason = reason
        where = f"registry entry '{entry_id}'" if entry_id else "source registry"
        super().__init__(f"Invalid {where}: {reason}")


class InvalidSettingsError(JobAggregatorError):
    """The settings file holds an unknown key or an invalid value."""

    def __init__(self, key: str, reason: str) -> None:
        self.key = key
        super().__init__(f"Invalid setting '{key}': {reason}")


class MissingSecretError(JobAggregatorError):
    """A required environment variable is absent or empty."""

    def __init__(self, variable_name: str) -> None:
        self.variable_name = variable_name
        super().__init__(f"Missing required secret: environment variable '{variable_name}' is not set")


class SourceBlockedError(JobAggregatorError):
    """A source answered with a login wall, a challenge page or a block status."""

    BLOCK_KINDS = ("login", "challenge", "ip")

    def __init__(self, source_id: str, reason: str, kind: str = "ip") -> None:
        """`kind`: login (a sign-in wall), challenge (captcha or human check) or ip (HTTP block, rate wall)."""
        self.source_id = source_id
        self.kind = kind
        super().__init__(f"Source '{source_id}' is blocked: {reason}")


class SourceTimeoutError(JobAggregatorError):
    """A source did not answer within the configured time."""

    def __init__(self, source_id: str, seconds: float) -> None:
        self.source_id = source_id
        super().__init__(f"Source '{source_id}' timed out after {seconds:g} seconds")


class AllTokensExhaustedError(JobAggregatorError):
    """Every token for a service hit a quota, rate limit or rejection during this run."""

    def __init__(self, service: str, token_count: int) -> None:
        self.service = service
        if token_count == 0:
            super().__init__(f"No tokens are configured for service '{service}'")
        else:
            super().__init__(f"All {token_count} token(s) for service '{service}' are exhausted for this run")


class ListingRejectedError(JobAggregatorError):
    """A listing failed validation and will not be stored."""

    def __init__(self, source_id: str, reason: str) -> None:
        self.source_id = source_id
        self.reason = reason
        super().__init__(f"Listing from source '{source_id}' rejected: {reason}")
