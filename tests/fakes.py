"""In-memory test doubles shared by several test modules."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Sequence
from typing import Any

UNIQUE_COLUMNS = {
    "jobs": ["dedupe_key"],
    "job_sources": ["url"],
    "runs": ["run_id"],
    "sources": ["id"],
    "linkedin_seen_posts": ["post_url"],
    "search_config": ["id"],
}
GENERATED_ID_TABLES = {"jobs", "job_sources", "source_runs"}


def _matches(row: dict, filters: Sequence[tuple[str, str, Any]]) -> bool:
    for column, operator, value in filters:
        actual = row.get(column)
        if operator == "eq" and actual != value:
            return False
        if operator == "neq" and actual == value:
            return False
        if operator == "in" and actual not in value:
            return False
        if operator == "is" and actual is not value:
            return False
        if operator in ("lt", "lte", "gt", "gte"):
            if actual is None:
                return False
            a, v = str(actual), str(value)
            if (operator == "lt" and not a < v) or (operator == "lte" and not a <= v) \
                    or (operator == "gt" and not a > v) or (operator == "gte" and not a >= v):
                return False
    return True


class FakeDatabaseClient:
    """Implements the `DatabaseClient` port in memory, enforcing the live unique constraints."""

    def __init__(self, tables: dict[str, list[dict]] | None = None) -> None:
        self.tables: dict[str, list[dict]] = copy.deepcopy(tables or {})
        self.calls: list[tuple[str, str]] = []

    def rows(self, table: str) -> list[dict]:
        return self.tables.setdefault(table, [])

    def select(self, table, columns="*", filters=(), order_by=None, descending=False, limit=None):
        self.calls.append(("select", table))
        found = [row for row in self.tables.get(table, []) if _matches(row, filters)]
        if order_by:
            found.sort(key=lambda r: str(r.get(order_by) or ""), reverse=descending)
        if limit is not None:
            found = found[:limit]
        if columns != "*":
            wanted = [c.strip() for c in columns.split(",")]
            found = [{c: row.get(c) for c in wanted} for row in found]
        return copy.deepcopy(found)

    def insert(self, table, rows):
        self.calls.append(("insert", table))
        inserted = []
        for row in rows:
            for column in UNIQUE_COLUMNS.get(table, []):
                if any(existing.get(column) == row.get(column) for existing in self.rows(table)):
                    raise ValueError(f"duplicate key value violates unique constraint on {table}.{column}")
            new_row = dict(row)
            if table in GENERATED_ID_TABLES:
                new_row.setdefault("id", str(uuid.uuid4()))
            self.rows(table).append(new_row)
            inserted.append(copy.deepcopy(new_row))
        return inserted

    def upsert(self, table, rows, on_conflict, ignore_duplicates=False):
        self.calls.append(("upsert", table))
        result = []
        for row in rows:
            existing = next((r for r in self.rows(table) if r.get(on_conflict) == row.get(on_conflict)), None)
            if existing is None:
                result += self.insert(table, [row])
            elif not ignore_duplicates:
                existing.update(row)
                result.append(copy.deepcopy(existing))
        return result

    def update(self, table, values, filters):
        self.calls.append(("update", table))
        updated = []
        for row in self.tables.get(table, []):
            if _matches(row, filters):
                row.update(values)
                updated.append(copy.deepcopy(row))
        return updated
