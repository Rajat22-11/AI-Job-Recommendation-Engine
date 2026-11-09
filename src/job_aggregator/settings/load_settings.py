"""Read `config/settings.yaml` into `AppSettings`, naming the offending key on any error."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from job_aggregator.domain.errors import InvalidSettingsError
from job_aggregator.settings.app_settings import AppSettings


def load_settings(path: str | Path) -> AppSettings:
    """Load and validate the settings file."""
    try:
        document = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise InvalidSettingsError("<file>", f"not valid YAML: {exc}") from exc
    return parse_settings(document)


def parse_settings(document: Any) -> AppSettings:
    """Validate an already-parsed settings document."""
    try:
        settings = AppSettings.model_validate(document)
    except ValidationError as exc:
        first = exc.errors()[0]
        key = ".".join(str(part) for part in first["loc"]) or "<root>"
        reason = "unknown key" if first["type"] == "extra_forbidden" else first["msg"]
        raise InvalidSettingsError(key, reason) from exc
    try:
        re.compile(settings.scoring.batch_pattern)
    except re.error as exc:
        raise InvalidSettingsError("scoring.batch_pattern", f"not a valid regular expression: {exc}") from exc
    return settings
