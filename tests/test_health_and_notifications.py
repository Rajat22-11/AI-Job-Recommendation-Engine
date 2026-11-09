from datetime import UTC, datetime, timedelta

import httpx

from job_aggregator.domain.models import RunStatus, RunSummary, SourceRunRecord, SourceStatus, TopMatch
from job_aggregator.health.evaluate_source_health import detect_missed_run, evaluate_source_health
from job_aggregator.notifications.notifier import (
    NtfyNotifier,
    format_run_summary,
    ping_heartbeat,
    send_notification_safely,
)
from job_aggregator.persistence.source_repository import SourceRepository
from job_aggregator.registry.source_entry import SourceEntry
from tests.fakes import FakeDatabaseClient

NOW = datetime(2026, 11, 8, 15, 0, tzinfo=UTC)


def _runs(*found):
    return [{"status": "ok", "jobs_found": n} for n in found]


def test_normal_source_is_healthy(app_settings):
    health = evaluate_source_health("indeed", SourceStatus.SUCCEEDED, 12, _runs(10, 14, 9), 0, app_settings.health)
    assert health == type(health)(0, None)


def test_source_at_zero_for_configured_runs_alerts(app_settings):
    threshold = app_settings.health.consecutive_empty_runs_alert
    health = evaluate_source_health("himalayas", SourceStatus.SUCCEEDED, 0, _runs(0, 0, 8), threshold - 1,
                                    app_settings.health)
    assert health.empty_run_streak == threshold
    assert "himalayas returned no jobs for" in health.alert


def test_far_below_baseline_alerts(app_settings):
    health = evaluate_source_health("jobcode", SourceStatus.SUCCEEDED, 1, _runs(20, 22, 18, 25), 0,
                                    app_settings.health)
    assert "far below its recent average" in health.alert


def test_skipped_run_keeps_streak(app_settings):
    health = evaluate_source_health("remotive", SourceStatus.SKIPPED, 0, [], 2, app_settings.health)
    assert health.empty_run_streak == 2 and health.alert is None


def test_missed_run_detected_from_stale_time(app_settings):
    hours = app_settings.health.missed_run_hours
    assert detect_missed_run(NOW - timedelta(hours=hours + 5), NOW, hours).startswith("No pipeline run recorded")
    assert detect_missed_run(NOW - timedelta(hours=2), NOW, hours) is None
    assert detect_missed_run(None, NOW, hours)


def _summary():
    return RunSummary(
        run_id="r1", status=RunStatus.PARTIAL, started_at=NOW, jobs_found=40, jobs_new=6, jobs_discarded=2,
        source_records=[SourceRunRecord(source_id="glassdoor", status=SourceStatus.BLOCKED, message="HTTP 403",
                                        started_at=NOW)],
        top_matches=[TopMatch(title="Java Developer", company="Acme", fit_score=5, apply_url="https://acme/1")],
    )


def test_notification_lists_count_top_matches_and_problem_sources():
    title, body, priority = format_run_summary(_summary(), ["himalayas returned no jobs for 3 runs in a row"])
    assert "6 new" in title
    assert "5/5 Java Developer at Acme" in body and "glassdoor: blocked" in body and "himalayas" in body
    assert priority == "high"


def test_ntfy_posts_one_message_to_topic():
    sent = []

    def handler(request):
        sent.append(request)
        return httpx.Response(200)

    NtfyNotifier("https://ntfy.sh", "secret-topic", transport=httpx.MockTransport(handler)).send(
        "Job run: 6 new job(s)", "body", "high")
    assert len(sent) == 1 and sent[0].url.path == "/secret-topic"
    assert sent[0].headers["Title"] == "Job run: 6 new job(s)" and sent[0].headers["Priority"] == "high"


def test_unreachable_channel_does_not_fail_the_run():
    def handler(request):
        raise httpx.ConnectError("unreachable")

    notifier = NtfyNotifier("https://ntfy.sh", "t", transport=httpx.MockTransport(handler))
    error = send_notification_safely(notifier, "t", "b", "default")
    assert error == "notification failed: ConnectError"


def test_heartbeat_called_after_success_and_skipped_without_url():
    pinged = []
    transport = httpx.MockTransport(lambda request: pinged.append(str(request.url)) or httpx.Response(200))
    assert ping_heartbeat("https://hc-ping.example/abc", True, transport) is True
    assert pinged == ["https://hc-ping.example/abc"]
    assert ping_heartbeat(None, True, transport) is False
    assert ping_heartbeat("https://hc-ping.example/abc", False, transport) is False
    assert len(pinged) == 1


def test_source_sync_writes_only_allowed_columns():
    db = FakeDatabaseClient({"sources": [{
        "id": "himalayas", "name": "Old", "base_url": "https://old", "enabled": False, "access_method": "public_scrape",
        "scrape_hints": {"keep": True}, "consecutive_empty_runs": 2, "notes": "keep me",
    }]})
    repo = SourceRepository(db)
    entries = [
        SourceEntry(id="himalayas", name="Himalayas", fetch_method="open_api", enabled=True,
                    base_url="https://himalayas.app", settings={"provider": "himalayas"}),
        SourceEntry(id="naukri", name="Naukri", fetch_method="jobspy_board", enabled=True,
                    base_url="https://www.naukri.com", settings={"site": "naukri"}),
    ]
    assert repo.sync_registry(entries) == {"created": 1, "updated": 1}
    rows = {row["id"]: row for row in db.rows("sources")}
    # The owner's UI edits (name, base_url, enabled=False) are kept; only access_method follows the registry.
    assert rows["himalayas"] == {
        "id": "himalayas", "name": "Old", "base_url": "https://old", "enabled": False,
        "access_method": "api", "scrape_hints": {"keep": True}, "consecutive_empty_runs": 2,
        "notes": "keep me",
    }
    assert rows["naukri"]["access_method"] == "connector" and rows["naukri"]["name"] == "Naukri"
    assert repo.enabled_flags(["himalayas", "naukri", "absent"]) == {"himalayas": False, "naukri": True}
    assert repo.sync_registry(entries) == {"created": 0, "updated": 0}  # a second run changes nothing
