"""Read and validate the source registry file. A malformed file stops the run before any fetch."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from job_aggregator.domain.errors import InvalidRegistryError
from job_aggregator.registry.source_entry import FETCH_METHOD_REQUIRED_SETTINGS, SourceEntry

REQUIRED_FIELDS = ("id", "name", "fetch_method", "enabled")
COMMON_FIELDS = {"id", "name", "fetch_method", "enabled", "base_url", "notes"}
SECRET_KEY_PATTERN = re.compile(r"(token|secret|password|passwd|api[_-]?key|cookie|session)", re.IGNORECASE)
SECRET_VALUE_PATTERN = re.compile(r"^(apify_api_[A-Za-z0-9]{10,}|AIza[0-9A-Za-z_\-]{20,}|eyJ[A-Za-z0-9_\-]{20,}\.)")


def load_source_registry(path: str | Path) -> list[SourceEntry]:
    """Load every entry from the registry file, validating it first."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise InvalidRegistryError(None, f"file is not valid YAML: {exc}") from exc
    return validate_source_registry(document)


def validate_source_registry(document: Any) -> list[SourceEntry]:
    """Turn the parsed registry document into entries, rejecting any malformed entry."""
    if not isinstance(document, dict) or not isinstance(document.get("sources"), list):
        raise InvalidRegistryError(None, "top-level key 'sources' must be a list")

    entries: list[SourceEntry] = []
    seen_ids: set[str] = set()
    for position, raw_entry in enumerate(document["sources"], start=1):
        entry = _validate_entry(raw_entry, position)
        if entry.id in seen_ids:
            raise InvalidRegistryError(entry.id, "duplicate identifier")
        seen_ids.add(entry.id)
        entries.append(entry)
    validate_not_fetched(document)
    return entries


def load_not_fetched(path: str | Path) -> dict[str, str]:
    """The `not_fetched` section: source id -> why the pipeline does not fetch it."""
    document = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return validate_not_fetched(document)


def validate_not_fetched(document: Any) -> dict[str, str]:
    section = (document or {}).get("not_fetched") or {}
    if not isinstance(section, dict) or not all(isinstance(k, str) and isinstance(v, str) and v.strip()
                                                for k, v in section.items()):
        raise InvalidRegistryError(None, "'not_fetched' must map each source id to a reason")
    fetched_ids = {entry.get("id") for entry in document.get("sources", []) if isinstance(entry, dict)}
    for source_id in section:
        if source_id in fetched_ids:
            raise InvalidRegistryError(source_id, "listed both in 'sources' and in 'not_fetched'")
    return dict(section)


def enabled_entries(entries: list[SourceEntry]) -> list[SourceEntry]:
    """Return only the entries whose enabled flag is true."""
    return [entry for entry in entries if entry.enabled]


def _validate_entry(raw_entry: Any, position: int) -> SourceEntry:
    if not isinstance(raw_entry, dict):
        raise InvalidRegistryError(f"#{position}", "entry must be a mapping")
    entry_label = str(raw_entry.get("id") or f"#{position}")

    for field_name in REQUIRED_FIELDS:
        if raw_entry.get(field_name) is None or raw_entry.get(field_name) == "":
            raise InvalidRegistryError(entry_label, f"missing required field '{field_name}'")
    if not isinstance(raw_entry["enabled"], bool):
        raise InvalidRegistryError(entry_label, "field 'enabled' must be true or false")

    fetch_method = raw_entry["fetch_method"]
    if fetch_method not in FETCH_METHOD_REQUIRED_SETTINGS:
        supported = ", ".join(sorted(FETCH_METHOD_REQUIRED_SETTINGS))
        raise InvalidRegistryError(entry_label, f"unsupported fetch method '{fetch_method}' (supported: {supported})")

    _reject_secrets(entry_label, raw_entry)

    settings = {key: value for key, value in raw_entry.items() if key not in COMMON_FIELDS}
    for setting_name in FETCH_METHOD_REQUIRED_SETTINGS[fetch_method]:
        if setting_name not in settings:
            raise InvalidRegistryError(
                entry_label, f"missing required field '{setting_name}' for fetch method '{fetch_method}'"
            )

    return SourceEntry(
        id=str(raw_entry["id"]),
        name=str(raw_entry["name"]),
        fetch_method=fetch_method,
        enabled=raw_entry["enabled"],
        base_url=str(raw_entry.get("base_url") or ""),
        settings=settings,
    )


def _reject_secrets(entry_label: str, raw_entry: dict[str, Any]) -> None:
    for key, value in raw_entry.items():
        if SECRET_KEY_PATTERN.search(str(key)):
            raise InvalidRegistryError(
                entry_label, f"field '{key}' looks like a secret; secrets belong in the environment"
            )
        if isinstance(value, str) and SECRET_VALUE_PATTERN.match(value):
            raise InvalidRegistryError(entry_label, f"field '{key}' holds what looks like a token value")
