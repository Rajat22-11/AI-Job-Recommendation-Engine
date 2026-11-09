"""The small database port the repositories depend on, and its Supabase (PostgREST) adapter."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal, Protocol

FilterOperator = Literal["eq", "neq", "lt", "lte", "gt", "gte", "in", "is"]
Filter = tuple[str, FilterOperator, Any]
Row = dict[str, Any]


class DatabaseClient(Protocol):
    """Table operations used by the repositories. Implemented by Supabase and by an in-memory fake."""

    def select(
        self,
        table: str,
        columns: str = "*",
        filters: Sequence[Filter] = (),
        order_by: str | None = None,
        descending: bool = False,
        limit: int | None = None,
    ) -> list[Row]: ...

    def insert(self, table: str, rows: list[Row]) -> list[Row]: ...

    def upsert(self, table: str, rows: list[Row], on_conflict: str, ignore_duplicates: bool = False) -> list[Row]: ...

    def update(self, table: str, values: Row, filters: Sequence[Filter]) -> list[Row]: ...


class SupabaseDatabaseClient:
    """`DatabaseClient` backed by supabase-py with the service key (bypasses row-level security)."""

    def __init__(self, url: str, service_key: str) -> None:
        from supabase import create_client  # imported here so tests never need the network client

        self._client = create_client(url, service_key)

    def select(self, table, columns="*", filters=(), order_by=None, descending=False, limit=None):
        query = self._apply_filters(self._client.table(table).select(columns), filters)
        if order_by:
            query = query.order(order_by, desc=descending)
        if limit is not None:
            query = query.limit(limit)
        return list(query.execute().data or [])

    def insert(self, table, rows):
        if not rows:
            return []
        return list(self._client.table(table).insert(rows).execute().data or [])

    def upsert(self, table, rows, on_conflict, ignore_duplicates=False):
        if not rows:
            return []
        query = self._client.table(table).upsert(rows, on_conflict=on_conflict, ignore_duplicates=ignore_duplicates)
        return list(query.execute().data or [])

    def update(self, table, values, filters):
        if not filters:
            raise ValueError("refusing to update every row of a table: no filters given")
        return list(self._apply_filters(self._client.table(table).update(values), filters).execute().data or [])

    @staticmethod
    def _apply_filters(query, filters: Sequence[Filter]):
        for column, operator, value in filters:
            if operator == "in":
                query = query.in_(column, list(value))
            elif operator == "is":
                query = query.is_(column, "null" if value is None else value)
            else:
                query = getattr(query, operator)(column, value)
        return query
