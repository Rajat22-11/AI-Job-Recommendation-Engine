"""Plain data models shared by every layer. No I/O happens here."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SourceStatus(str, Enum):
    """Outcome of one source within one run, as stored in `source_runs.status`."""

    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class RunStatus(str, Enum):
    """Lifecycle state of a run, as stored in `runs.status`."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class SearchConfig(BaseModel):
    """The owner's search criteria, read from the single `search_config` row."""

    keywords: list[str]
    locations: list[str]
    min_salary_lpa: float
    max_required_yoe: float
    max_job_age_days: int
    excluded_companies: list[str] = Field(default_factory=list)


class RawListing(BaseModel):
    """A job exactly as one source described it, in the common raw shape every fetcher returns."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    title: str
    company: str
    apply_url: str
    source_url: str | None = None
    external_id: str | None = None
    location: str | None = None
    description: str | None = None
    salary_text: str | None = None
    employment_type: str | None = None
    experience_text: str | None = None
    skills: list[str] = Field(default_factory=list)
    posted_at: date | None = None
    is_remote: bool | None = None
    apply_url_kind: str | None = None


class NormalizedJob(BaseModel):
    """A listing converted to the `jobs` table fields, ready to dedupe, score and store."""

    model_config = ConfigDict(extra="forbid")

    dedupe_key: str
    title: str
    company: str
    apply_url: str
    location: str | None = None
    location_bucket: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    role_track: str | None = None
    min_yoe: float | None = None
    max_yoe: float | None = None
    salary_text: str | None = None
    salary_min_lpa: float | None = None
    salary_max_lpa: float | None = None
    salary_meets_min: bool | None = None
    skills: list[str] = Field(default_factory=list)
    summary: str | None = None
    posted_at: date | None = None
    apply_url_kind: str | None = None
    fit_score: int | None = Field(default=None, ge=1, le=5)
    fit_reason: str | None = None
    source_id: str
    source_url: str
    external_id: str | None = None


class FetchResult(BaseModel):
    """What one fetcher returned for one source: listings plus a status and a message."""

    source_id: str
    status: SourceStatus
    listings: list[RawListing] = Field(default_factory=list)
    message: str = ""
    block_kind: str | None = None  # for BLOCKED: "login", "challenge" or "ip"


class SourceRunRecord(BaseModel):
    """Per-source counts for one run, stored as one `source_runs` row."""

    source_id: str
    status: SourceStatus
    jobs_found: int = 0
    jobs_new: int = 0
    message: str = ""
    block_kind: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


class TopMatch(BaseModel):
    """A short reference to a high-scoring job, used in the notification."""

    title: str
    company: str
    fit_score: int
    apply_url: str


class RunSummary(BaseModel):
    """Totals for one run, used for the `runs` row and the notification."""

    run_id: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    jobs_found: int = 0
    jobs_new: int = 0
    jobs_discarded: int = 0
    source_records: list[SourceRunRecord] = Field(default_factory=list)
    top_matches: list[TopMatch] = Field(default_factory=list)
    unhealthy_sources: list[str] = Field(default_factory=list)
    notification_error: str | None = None
    dry_run: bool = False
