"""Typed model of `config/settings.yaml`. Unknown keys are rejected so typos never pass silently."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FetchingSettings(_Strict):
    request_timeout_seconds: float = Field(gt=0)
    max_retries: int = Field(ge=0, le=10)
    retry_backoff_seconds: float = Field(ge=0)
    pacing_seconds: float = Field(ge=0)
    max_listings_per_source: int = Field(gt=0)
    user_agent: str


class MatchingSettings(_Strict):
    generic_words: list[str]
    prefilter_min_ratio: float = Field(gt=0, le=1)
    score_min_ratio: float = Field(gt=0, le=1)


class JobSpySettings(_Strict):
    country: str
    results_wanted: int = Field(gt=0)
    hours_old: int = Field(gt=0)
    max_searches_per_board: int = Field(gt=0)


class FieldAliases(_Strict):
    company: list[str]
    role: list[str]
    experience: list[str]
    batch: list[str]
    location: list[str]
    skills: list[str]
    stipend: list[str]
    apply_link: list[str]


class LinkedInSettings(_Strict):
    apify_actor_id: str
    max_posts_per_run: int = Field(gt=0)
    default_posts_per_profile: int = Field(gt=0)
    short_link_timeout_seconds: float = Field(gt=0)
    hiring_markers: list[str] = Field(min_length=1)
    field_aliases: FieldAliases


LOCATION_BUCKETS_ALLOWED = ("pune", "mumbai", "gujarat", "remote_india", "remote_international", "other")
ROLE_TRACKS_ALLOWED = ("java_backend", "ml_ai", "data", "full_stack", "other")


class ProcessingSettings(_Strict):
    remote_location_words: list[str]
    hybrid_location_words: list[str]
    known_cities: list[str]
    location_buckets: dict[str, list[str]]
    india_words: list[str]
    remote_without_country_bucket: Literal["remote_india", "remote_international"]
    role_tracks: dict[str, list[str]]
    usd_to_inr: float = Field(gt=0)

    @field_validator("location_buckets")
    @classmethod
    def _buckets_allowed_by_database(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        unknown = set(value) - set(LOCATION_BUCKETS_ALLOWED)
        if unknown:
            raise ValueError(f"bucket(s) {sorted(unknown)} not allowed by jobs.location_bucket")
        return value

    @field_validator("role_tracks")
    @classmethod
    def _tracks_allowed_by_database(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        unknown = set(value) - set(ROLE_TRACKS_ALLOWED)
        if unknown:
            raise ValueError(f"track(s) {sorted(unknown)} not allowed by jobs.role_track")
        return value


class PersistenceSettings(_Strict):
    stale_after_days_unseen: int = Field(gt=0)


class ScoringWeights(_Strict):
    keyword_match: float
    no_keyword_match: float
    location_match: float
    location_mismatch: float
    experience_over_limit: float
    salary_meets_min: float
    salary_below_min: float
    internship_or_batch: float
    senior_title: float = 0.0


class GeminiSettings(_Strict):
    enabled: bool
    model: str
    max_jobs_per_run: int = Field(ge=0)
    request_timeout_seconds: float = Field(gt=0)
    min_seconds_between_calls: float = Field(default=0.0, ge=0)


class ScoringSettings(_Strict):
    weights: ScoringWeights
    internship_words: list[str]
    seniority_words: list[str] = Field(default_factory=list)
    batch_pattern: str
    borderline_scores: list[int]
    gemini: GeminiSettings


class HealthSettings(_Strict):
    consecutive_empty_runs_alert: int = Field(gt=0)
    baseline_runs: int = Field(gt=0)
    low_ratio_alert: float = Field(gt=0, lt=1)
    missed_run_hours: float = Field(gt=0)


class NotificationSettings(_Strict):
    channel: Literal["ntfy", "none"]
    ntfy_server: str
    top_matches_count: int = Field(ge=0)
    min_score_for_top_match: int = Field(ge=1, le=5)
    heartbeat_enabled: bool


class TriggerSettings(_Strict):
    start_wait_seconds: int = Field(gt=0)
    start_retry_interval_seconds: int = Field(gt=0)
    poll_interval_seconds: int = Field(gt=0)
    poll_limit_minutes: int = Field(gt=0)
    repeat_trigger_behaviour: Literal["return_finished", "start_new"]
    schedule_hint: str
    stale_running_minutes: int = Field(gt=0)


class AppSettings(_Strict):
    """All non-secret behaviour settings."""

    fetching: FetchingSettings
    matching: MatchingSettings
    jobspy: JobSpySettings
    linkedin: LinkedInSettings
    processing: ProcessingSettings
    persistence: PersistenceSettings
    scoring: ScoringSettings
    health: HealthSettings
    notifications: NotificationSettings
    trigger: TriggerSettings
