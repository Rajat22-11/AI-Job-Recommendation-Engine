"""Read the owner's search criteria from the single `search_config` row (id = 1)."""

from __future__ import annotations

from job_aggregator.domain.models import SearchConfig
from job_aggregator.persistence.database_client import DatabaseClient


class SearchConfigRepository:
    def __init__(self, database: DatabaseClient) -> None:
        self._db = database

    def load_search_config(self) -> SearchConfig:
        rows = self._db.select("search_config", "*", [("id", "eq", 1)], limit=1)
        if not rows:
            raise LookupError("search_config row with id = 1 is missing")
        row = rows[0]
        return SearchConfig(
            keywords=row.get("keywords") or [],
            locations=row.get("locations") or [],
            min_salary_lpa=float(row["min_salary_lpa"]),
            max_required_yoe=float(row["max_required_yoe"]),
            max_job_age_days=int(row["max_job_age_days"]),
            excluded_companies=row.get("excluded_companies") or [],
        )
