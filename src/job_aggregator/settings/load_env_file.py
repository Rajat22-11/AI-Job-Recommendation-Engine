"""Load secrets from a local `.env.local` file into the process environment.

The file is optional and exists for local runs. On Render the variables come from the service's own
environment and no file is present. A variable already set in the real environment always wins over the file,
so the same code behaves the same in both places. Values are never logged.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import MutableMapping
from pathlib import Path

logger = logging.getLogger(__name__)

ENV_FILE_VARIABLE = "JOB_AGGREGATOR_ENV_FILE"
DEFAULT_ENV_FILE_NAMES = (".env.local", ".env")
PROJECT_ROOT = Path(__file__).resolve().parents[3]

_ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def parse_env_file_text(text: str) -> dict[str, str]:
    """Parse NAME=value lines. Blank lines and `#` comments are ignored; matching quotes are removed."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _ASSIGNMENT.match(line)
        if not match:
            continue
        name, raw = match.groups()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
            raw = raw[1:-1]
        elif " #" in raw:
            raw = raw.split(" #", 1)[0].rstrip()
        values[name] = raw
    return values


def find_env_file(environ: MutableMapping[str, str] | None = None, cwd: Path | None = None) -> Path | None:
    """The file named by JOB_AGGREGATOR_ENV_FILE, else `.env.local` then `.env` (working folder, then project root)."""
    env = os.environ if environ is None else environ
    explicit = env.get(ENV_FILE_VARIABLE, "").strip()
    if explicit:
        return Path(explicit)
    for folder in ((cwd or Path.cwd()), PROJECT_ROOT):
        for name in DEFAULT_ENV_FILE_NAMES:
            candidate = folder / name
            if candidate.is_file():
                return candidate
    return None


def load_env_file(environ: MutableMapping[str, str] | None = None, path: Path | None = None) -> list[str]:
    """Copy file values into `environ` without overriding variables already set to a non-empty value.

    Returns the names that were loaded (never the values).
    """
    env = os.environ if environ is None else environ
    file_path = path or find_env_file(env)
    if file_path is None or not file_path.is_file():
        return []
    loaded: list[str] = []
    for name, value in parse_env_file_text(file_path.read_text(encoding="utf-8-sig")).items():
        if env.get(name, "").strip() or not value:
            continue
        env[name] = value
        loaded.append(name)
    logger.info("loaded %d variable(s) from %s: %s", len(loaded), file_path.name, ", ".join(sorted(loaded)))
    return loaded
