"""Command-line check of the registry file: prints every entry or the first validation error.

Usage: python -m job_aggregator.registry.check_source_registry [path]
"""

from __future__ import annotations

import sys

from job_aggregator.domain.errors import InvalidRegistryError
from job_aggregator.registry.load_source_registry import load_source_registry

DEFAULT_PATH = "config/sources.yaml"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    path = args[0] if args else DEFAULT_PATH
    try:
        entries = load_source_registry(path)
    except InvalidRegistryError as exc:
        print(f"INVALID: {exc}")
        return 1
    for entry in entries:
        state = "enabled " if entry.enabled else "disabled"
        print(f"{state}  {entry.id:<24} {entry.fetch_method:<24} {entry.name}")
    print(f"OK: {len(entries)} entries, {sum(e.enabled for e in entries)} enabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
