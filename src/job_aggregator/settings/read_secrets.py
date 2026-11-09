"""Read secrets from environment variables. Values are never logged or returned in messages."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

from job_aggregator.domain.errors import MissingSecretError

LIST_SEPARATOR = re.compile(r"[,\n;]")

SUPABASE_URL = "SUPABASE_URL"
SUPABASE_SERVICE_KEY = "SUPABASE_SERVICE_KEY"
APIFY_TOKENS = "APIFY_TOKENS"
GEMINI_API_KEYS = "GEMINI_API_KEYS"
NTFY_TOPIC = "NTFY_TOPIC"
TRIGGER_SECRETS = "TRIGGER_SECRETS"
HEARTBEAT_URL = "HEARTBEAT_URL"

SERVICE_TOKEN_VARIABLES: dict[str, str] = {"apify": APIFY_TOKENS, "gemini": GEMINI_API_KEYS}
"""Credential service name -> environment variable holding its token list."""


def read_secret_list(name: str, environ: Mapping[str, str] | None = None, *, required: bool = True) -> list[str]:
    """Read one variable holding one or more values separated by commas, semicolons or newlines."""
    env = os.environ if environ is None else environ
    values = [part.strip() for part in LIST_SEPARATOR.split(env.get(name, "")) if part.strip()]
    if required and not values:
        raise MissingSecretError(name)
    return values


def read_secret(name: str, environ: Mapping[str, str] | None = None, *, required: bool = True) -> str | None:
    """Read one single-valued secret."""
    env = os.environ if environ is None else environ
    value = env.get(name, "").strip()
    if required and not value:
        raise MissingSecretError(name)
    return value or None


@dataclass(frozen=True, repr=False)
class PipelineSecrets:
    """Secrets the pipeline needs. `repr` is hidden so values never reach a log by accident."""

    supabase_url: str
    supabase_service_key: str
    service_tokens: dict[str, list[str]]
    ntfy_topic: str | None
    heartbeat_url: str | None

    def __repr__(self) -> str:
        counts = {service: len(tokens) for service, tokens in self.service_tokens.items()}
        return f"PipelineSecrets(token_counts={counts}, ntfy_topic_set={self.ntfy_topic is not None})"


def read_secret_lists_from_environment(environ: Mapping[str, str] | None = None) -> PipelineSecrets:
    """Read every pipeline secret. Token lists may be empty; the pool fails only the services that need them."""
    return PipelineSecrets(
        supabase_url=read_secret(SUPABASE_URL, environ) or "",
        supabase_service_key=read_secret(SUPABASE_SERVICE_KEY, environ) or "",
        service_tokens={
            service: read_secret_list(variable, environ, required=False)
            for service, variable in SERVICE_TOKEN_VARIABLES.items()
        },
        ntfy_topic=read_secret(NTFY_TOPIC, environ, required=False),
        heartbeat_url=read_secret(HEARTBEAT_URL, environ, required=False),
    )


def read_trigger_secrets(environ: Mapping[str, str] | None = None) -> list[str]:
    """Read the shared secrets the service accepts; at least one is required to start the service."""
    return read_secret_list(TRIGGER_SECRETS, environ)
