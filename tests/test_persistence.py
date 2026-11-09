from datetime import UTC, date, datetime, timedelta

from job_aggregator.domain.models import NormalizedJob, SourceRunRecord, SourceStatus
from job_aggregator.persistence.job_repository import JobRepository
from job_aggregator.persistence.run_repository import RunRepository, database_source_status
from job_aggregator.persistence.search_config_repository import SearchConfigRepository
from job_aggregator.persistence.seen_post_repository import SeenPostRepository
from tests.fakes import FakeDatabaseClient

NOW = datetime(2026, 11, 8, 15, 0, tzinfo=UTC)


def _job(key="acme|java developer|pune", source="indeed", url="https://in.indeed.com/1", **extra):
    company, title, location = key.split("|")
    return NormalizedJob(dedupe_key=key, title=title, company=company, location=location,
                         apply_url=url, source_id=source, source_url=url, **extra)


def test_same_job_from_two_sources_stored_once_with_two_links():
    db = FakeDatabaseClient()
    result = JobRepository(db).store_jobs(
        [_job(), _job(source="naukri", url="https://naukri.com/1")], NOW
    )
    assert result.new_keys == ["acme|java developer|pune"]
    assert len(db.rows("jobs")) == 1
    assert {link["source_id"] for link in db.rows("job_sources")} == {"indeed", "naukri"}


def test_repeated_writes_create_no_duplicates_and_update_last_seen():
    db = FakeDatabaseClient()
    repo = JobRepository(db)
    repo.store_jobs([_job(), _job("beta|data engineer|mumbai", url="https://in.indeed.com/2")], NOW)
    later = NOW + timedelta(days=1)
    result = repo.store_jobs([_job(), _job("beta|data engineer|mumbai", url="https://in.indeed.com/2")], later)
    assert result.new_keys == []
    assert sorted(result.seen_again_keys) == ["acme|java developer|pune", "beta|data engineer|mumbai"]
    assert len(db.rows("jobs")) == 2 and len(db.rows("job_sources")) == 2
    assert all(row["last_seen_at"] == later.isoformat() for row in db.rows("jobs"))


def test_restart_after_partial_failure_stores_remaining_only():
    db = FakeDatabaseClient()
    repo = JobRepository(db)
    repo.store_jobs([_job()], NOW)
    result = repo.store_jobs([_job(), _job("gamma|ml engineer|remote", url="https://x/3")], NOW)
    assert result.new_keys == ["gamma|ml engineer|remote"]
    assert len(db.rows("jobs")) == 2


def test_retire_stale_jobs_marks_old_inactive_and_keeps_recent():
    db = FakeDatabaseClient()
    repo = JobRepository(db)
    repo.store_jobs([_job(posted_at=date(2026, 9, 1)), _job("fresh|dev|pune", url="https://x/2",
                                                              posted_at=date(2026, 11, 7))], NOW)
    retired = repo.retire_stale_jobs(NOW, max_job_age_days=30, stale_after_days_unseen=21)
    by_key = {row["dedupe_key"]: row for row in db.rows("jobs")}
    assert retired == 1
    assert by_key["acme|java developer|pune"]["is_active"] is False
    assert by_key["fresh|dev|pune"]["is_active"] is True
    assert len(db.rows("jobs")) == 2


def test_retire_by_last_seen():
    db = FakeDatabaseClient()
    repo = JobRepository(db)
    repo.store_jobs([_job()], NOW - timedelta(days=40))
    assert repo.retire_stale_jobs(NOW, max_job_age_days=365, stale_after_days_unseen=21) == 1


def test_run_repository_records_rows_with_database_statuses():
    db = FakeDatabaseClient()
    runs = RunRepository(db)
    runs.start_run("r1", "github-cron", NOW, {"sources": 3})
    runs.record_source_run("r1", SourceRunRecord(source_id="indeed", status=SourceStatus.SUCCEEDED,
                                                 jobs_found=5, jobs_new=2, started_at=NOW, finished_at=NOW))
    for source, kind in (("glassdoor", "challenge"), ("naukri", "login"), ("monster", "ip")):
        runs.record_source_run("r1", SourceRunRecord(source_id=source, status=SourceStatus.BLOCKED,
                                                     message="blocked", block_kind=kind, started_at=NOW))
    # Only a sign-in wall asks the UI banner to "log in"; an IP block is an error with its reason in the message.
    assert [row["status"] for row in db.rows("source_runs")] == ["ok", "captcha", "needs_login", "error"]
    assert runs.running_runs()[0]["run_id"] == "r1"
    runs.mark_interrupted("r1", NOW, "service restarted")
    assert runs.get_run("r1")["status"] == "interrupted"
    assert database_source_status(SourceStatus.FAILED) == "error"


def test_seen_posts_recorded_once():
    db = FakeDatabaseClient()
    seen = SeenPostRepository(db)
    seen.record_post("https://linkedin.com/p/1", "li_x", "job_created", NOW, job_id="j1")
    seen.record_post("https://linkedin.com/p/1", "li_x", "job_created", NOW, job_id="j1")
    assert len(db.rows("linkedin_seen_posts")) == 1
    assert seen.find_seen_post_urls(["https://linkedin.com/p/1", "https://linkedin.com/p/2"]) == {
        "https://linkedin.com/p/1"}


def test_search_config_loaded():
    db = FakeDatabaseClient({"search_config": [{
        "id": 1, "keywords": ["java"], "locations": ["Pune"], "min_salary_lpa": 8.2, "max_required_yoe": 3,
        "max_job_age_days": 30, "excluded_companies": ["BadCo"],
    }]})
    config = SearchConfigRepository(db).load_search_config()
    assert config.keywords == ["java"] and config.max_required_yoe == 3.0
