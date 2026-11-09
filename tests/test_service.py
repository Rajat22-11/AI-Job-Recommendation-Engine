import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from job_aggregator.domain.models import RunStatus, RunSummary
from job_aggregator.persistence.run_repository import RunRepository
from job_aggregator.service.run_manager import RunManager
from job_aggregator.service.shared_secret_auth import is_valid_secret
from job_aggregator.service.web_app import create_app
from tests.fakes import FakeDatabaseClient

NOW = datetime(2026, 11, 8, 15, 0, tzinfo=UTC)
SECRETS = ["old-secret-value", "new-secret-value"]


class ManualThreads:
    """Runs a started thread only when told, so tests can observe the 'running' state."""

    def __init__(self):
        self.pending = []

    def __call__(self, target):
        self.pending.append(target)

    def run_all(self):
        while self.pending:
            self.pending.pop(0)()


def _fake_pipeline(runs: RunRepository, status=RunStatus.SUCCEEDED, calls=None, error=None):
    def run(options):
        if calls is not None:
            calls.append(options)
        if error:
            raise error
        runs.start_run(options.run_id, options.trigger_id, NOW, {})
        runs.finish_run(options.run_id, status, NOW, '{"jobs_new": 2}', True)
        return RunSummary(run_id=options.run_id, status=status, started_at=NOW, finished_at=NOW, jobs_new=2)
    return run


def _manager(app_settings, db=None, behaviour="return_finished", **pipeline_kwargs):
    db = db or FakeDatabaseClient()
    runs = RunRepository(db)
    threads = ManualThreads()
    settings = app_settings.trigger.model_copy(update={"repeat_trigger_behaviour": behaviour})
    manager = RunManager(_fake_pipeline(runs, **pipeline_kwargs), runs, settings, clock=lambda: NOW,
                         start_thread=threads)
    return manager, threads, db


# ---------------- run manager ----------------

def test_start_returns_run_id_and_runs_in_background(app_settings):
    calls = []
    manager, threads, db = _manager(app_settings, calls=calls)
    outcome = manager.start("github-cron")
    assert outcome.started and outcome.state == "running" and calls == []
    assert manager.status(outcome.run_id)["state"] == "running"
    threads.run_all()
    assert calls[0].run_id == outcome.run_id and calls[0].trigger_id == "service:github-cron"
    status = manager.status(outcome.run_id)
    assert status["state"] == "succeeded" and status["jobs_new"] == 2


def test_service_skip_methods_applied_to_every_run(app_settings):
    calls = []
    db = FakeDatabaseClient()
    runs = RunRepository(db)
    threads = ManualThreads()
    manager = RunManager(_fake_pipeline(runs, calls=calls), runs, app_settings.trigger, clock=lambda: NOW,
                         start_thread=threads, skip_methods=("jobspy_board",))
    manager.start()
    threads.run_all()
    assert calls[0].skip_methods == ("jobspy_board",)


def test_second_start_during_run_is_refused(app_settings):
    manager, threads, _ = _manager(app_settings)
    first = manager.start()
    second = manager.start()
    assert not second.started and second.run_id == first.run_id and len(threads.pending) == 1


def test_run_started_elsewhere_blocks_a_new_start(app_settings):
    db = FakeDatabaseClient({"runs": [{"run_id": "pc-run", "trigger_id": "cli", "status": "running",
                                       "started_at": (NOW - timedelta(minutes=10)).isoformat()}]})
    manager, threads, _ = _manager(app_settings, db)
    outcome = manager.start()
    assert not outcome.started and outcome.run_id == "pc-run" and threads.pending == []


@pytest.mark.parametrize(("behaviour", "starts_again"), [("return_finished", False), ("start_new", True)])
def test_repeat_trigger_after_finish_follows_setting(app_settings, behaviour, starts_again):
    manager, threads, _ = _manager(app_settings, behaviour=behaviour)
    first = manager.start()
    threads.run_all()
    again = manager.start()
    assert again.started is starts_again
    if not starts_again:
        assert again.run_id == first.run_id and again.state == "succeeded"
    threads.run_all()
    assert manager.start(force=True).started


def test_failed_run_reported_and_crash_recorded(app_settings):
    manager, threads, _ = _manager(app_settings, error=RuntimeError("database down"))
    outcome = manager.start()
    threads.run_all()
    status = manager.status(outcome.run_id)
    assert status["state"] == "failed" and "database down" in status["error"]


def test_restart_marks_only_service_runs_interrupted(app_settings):
    db = FakeDatabaseClient({"runs": [
        {"run_id": "svc", "trigger_id": "service:github-cron", "status": "running",
         "started_at": (NOW - timedelta(minutes=5)).isoformat()},
        {"run_id": "pc", "trigger_id": "cli", "status": "running",
         "started_at": (NOW - timedelta(minutes=5)).isoformat()},
        {"run_id": "old-pc", "trigger_id": "cli", "status": "running",
         "started_at": (NOW - timedelta(hours=5)).isoformat()},
    ]})
    manager, _, db = _manager(app_settings, db)
    assert manager.recover_interrupted_runs() == ["svc"]
    states = {row["run_id"]: row["status"] for row in db.rows("runs")}
    # Rows from the PC or the old Claude routine are history and are never rewritten.
    assert states == {"svc": "interrupted", "pc": "running", "old-pc": "running"}


def test_status_of_service_run_left_running_after_restart_is_interrupted(app_settings):
    db = FakeDatabaseClient({"runs": [{"run_id": "svc", "trigger_id": "service:x", "status": "running",
                                       "started_at": NOW.isoformat()}]})
    manager, _, _ = _manager(app_settings, db)
    assert manager.status("svc")["state"] == "interrupted"
    assert manager.status("nope") is None


# ---------------- endpoints and auth ----------------

def _client(app_settings, health_alerts=None):
    manager, threads, db = _manager(app_settings)
    app = create_app(manager, lambda: health_alerts or [], SECRETS)
    return TestClient(app), threads


def _auth(secret):
    return {"Authorization": f"Bearer {secret}"}


def test_liveness_needs_no_secret_and_returns_no_data(app_settings):
    client, _ = _client(app_settings)
    response = client.get("/healthz")
    assert response.status_code == 204 and response.content == b""


@pytest.mark.parametrize("headers", [{}, _auth("wrong-secret"), {"Authorization": "Basic old-secret-value"}])
def test_missing_or_wrong_secret_rejected_and_nothing_starts(app_settings, headers):
    client, threads = _client(app_settings)
    assert client.post("/runs", headers=headers).status_code == 401
    assert client.get("/runs/abc", headers=headers).status_code == 401
    assert client.post("/health-check", headers=headers).status_code == 401
    assert threads.pending == []


@pytest.mark.parametrize("secret", SECRETS)
def test_either_of_two_secrets_accepted(app_settings, secret):
    client, threads = _client(app_settings)
    response = client.post("/runs", headers=_auth(secret), json={"trigger_id": "github-cron"})
    assert response.status_code == 202
    body = response.json()
    assert body["started"] is True and body["run_id"]
    assert client.get(f"/runs/{body['run_id']}", headers=_auth(secret)).json()["state"] == "running"
    threads.run_all()
    assert client.get(f"/runs/{body['run_id']}", headers=_auth(secret)).json()["state"] == "succeeded"


def test_overlap_refused_through_endpoint(app_settings):
    client, _ = _client(app_settings)
    first = client.post("/runs", headers=_auth(SECRETS[0])).json()
    second = client.post("/runs", headers=_auth(SECRETS[0])).json()
    assert second["started"] is False and second["run_id"] == first["run_id"]


def test_health_check_endpoint_and_unknown_run(app_settings):
    client, _ = _client(app_settings, health_alerts=["No pipeline run recorded for 30 hours"])
    assert client.post("/health-check", headers=_auth(SECRETS[1])).json() == {
        "alerts": ["No pipeline run recorded for 30 hours"]}
    assert client.get("/runs/unknown", headers=_auth(SECRETS[1])).status_code == 404


def test_no_secret_appears_in_logs_or_responses(app_settings, caplog):
    client, threads = _client(app_settings)
    with caplog.at_level(logging.DEBUG):
        responses = [client.post("/runs", headers=_auth(SECRETS[0])),
                     client.post("/runs", headers=_auth("attacker-guess")),
                     client.post("/health-check", headers=_auth(SECRETS[1]))]
        threads.run_all()
    text = caplog.text + "".join(r.text for r in responses)
    assert all(secret not in text for secret in SECRETS + ["attacker-guess"])


def test_constant_time_check_accepts_only_exact_matches():
    assert is_valid_secret("new-secret-value", SECRETS)
    assert not is_valid_secret("new-secret-valu", SECRETS)
    assert not is_valid_secret(None, SECRETS)
    assert not is_valid_secret("", SECRETS)


def test_app_requires_at_least_one_secret(app_settings):
    manager, _, _ = _manager(app_settings)
    with pytest.raises(ValueError):
        create_app(manager, lambda: [], [])
