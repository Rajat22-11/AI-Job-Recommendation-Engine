from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from job_aggregator.domain.errors import (
    AllTokensExhaustedError,
    InvalidRegistryError,
    ListingRejectedError,
    SourceBlockedError,
    SourceTimeoutError,
)
from job_aggregator.domain.models import (
    FetchResult,
    NormalizedJob,
    RawListing,
    RunStatus,
    RunSummary,
    SourceStatus,
)


def test_builds_each_model():
    raw = RawListing(source_id="himalayas", title="Dev", company="Acme", apply_url="https://a.example")
    job = NormalizedJob(
        dedupe_key="acme|dev|remote", title="Dev", company="Acme", apply_url="https://a.example",
        source_id="himalayas", source_url="https://a.example",
    )
    result = FetchResult(source_id="himalayas", status=SourceStatus.SUCCEEDED, listings=[raw])
    summary = RunSummary(run_id="r1", status=RunStatus.RUNNING, started_at=datetime.now(UTC))
    assert result.listings[0].title == "Dev"
    assert job.skills == []
    assert summary.jobs_new == 0


@pytest.mark.parametrize("missing", ["title", "company", "apply_url", "source_id"])
def test_raw_listing_rejects_missing_required_field(missing):
    data = {"source_id": "s", "title": "t", "company": "c", "apply_url": "u"}
    del data[missing]
    with pytest.raises(ValidationError):
        RawListing(**data)


def test_normalized_job_rejects_missing_dedupe_key_and_bad_score():
    base = {"title": "t", "company": "c", "apply_url": "u", "source_id": "s", "source_url": "u"}
    with pytest.raises(ValidationError):
        NormalizedJob(**base)
    with pytest.raises(ValidationError):
        NormalizedJob(dedupe_key="k", fit_score=7, **base)


def test_fetch_result_and_summary_reject_missing_fields():
    with pytest.raises(ValidationError):
        FetchResult(source_id="s")
    with pytest.raises(ValidationError):
        RunSummary(run_id="r", status=RunStatus.RUNNING)


@pytest.mark.parametrize(
    ("error", "name"),
    [
        (InvalidRegistryError("li_x", "missing field 'name'"), "li_x"),
        (SourceBlockedError("glassdoor", "HTTP 403"), "glassdoor"),
        (SourceTimeoutError("remotive", 30), "remotive"),
        (AllTokensExhaustedError("apify", 2), "apify"),
        (ListingRejectedError("jobcode", "no apply URL"), "jobcode"),
    ],
)
def test_error_messages_name_the_entry_or_service(error, name):
    assert name in str(error)
