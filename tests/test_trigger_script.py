"""The GitHub trigger script: wake-up retries, polling, and visible failure, using a scripted fake HTTP layer."""

import importlib.util

import pytest

from tests.conftest import REPO_ROOT

spec = importlib.util.spec_from_file_location("trigger_and_wait", REPO_ROOT / "scripts" / "trigger_and_wait.py")
trigger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trigger)

SETTINGS = {"start_wait_seconds": 60, "start_retry_interval_seconds": 10, "poll_interval_seconds": 30,
            "poll_limit_minutes": 5}


class Clock:
    def __init__(self):
        self.now = 0.0

    def sleep(self, seconds):
        self.now += seconds

    def __call__(self):
        return self.now


def _script(monkeypatch, answers):
    calls = []

    def fake_http(method, url, secret, body=None, timeout=30):
        calls.append((method, url))
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(trigger, "http_json", fake_http)
    return calls


def test_wakes_sleeping_service_then_polls_until_finished(monkeypatch, capsys):
    clock = Clock()
    calls = _script(monkeypatch, [
        trigger.Unreachable("HTTP 502"), trigger.Unreachable("timeout"),
        (202, {"run_id": "r1", "started": True, "state": "running"}),
        (200, {"state": "running"}), (200, {"state": "partial", "summary": "{}"}),
    ])
    assert trigger.run_and_wait("https://svc", "s", SETTINGS, clock.sleep, clock) == 0
    assert [c[0] for c in calls] == ["POST", "POST", "POST", "GET", "GET"]
    out = capsys.readouterr().out
    assert "retrying" in out and "::warning::run r1 finished partial" in out


def test_unreachable_service_fails_visibly(monkeypatch, capsys):
    clock = Clock()
    _script(monkeypatch, [trigger.Unreachable("timeout")] * 20)
    with pytest.raises(trigger.Unreachable, match="no answer after"):
        trigger.run_and_wait("https://svc", "s", SETTINGS, clock.sleep, clock)


@pytest.mark.parametrize("final_state", ["failed", "interrupted"])
def test_failed_or_interrupted_run_fails_workflow(monkeypatch, capsys, final_state):
    clock = Clock()
    _script(monkeypatch, [(202, {"run_id": "r1", "state": "running"}), (200, {"state": final_state})])
    assert trigger.run_and_wait("https://svc", "s", SETTINGS, clock.sleep, clock) == 1
    assert f"::error::run r1 ended {final_state}" in capsys.readouterr().out


def test_run_still_running_at_limit_fails_and_names_run(monkeypatch, capsys):
    clock = Clock()
    _script(monkeypatch, [(202, {"run_id": "r9", "state": "running"})] + [(200, {"state": "running"})] * 50)
    assert trigger.run_and_wait("https://svc", "s", SETTINGS, clock.sleep, clock) == 1
    assert "::error::run r9 did not finish within 5 minutes" in capsys.readouterr().out


def test_rejected_secret_fails_without_retry(monkeypatch, capsys):
    clock = Clock()
    calls = _script(monkeypatch, [(401, {"detail": "missing or invalid secret"})])
    assert trigger.run_and_wait("https://svc", "s", SETTINGS, clock.sleep, clock) == 1
    assert len(calls) == 1 and "401" in capsys.readouterr().out


def test_already_finished_today_returns_success(monkeypatch):
    clock = Clock()
    calls = _script(monkeypatch, [(202, {"run_id": "r1", "started": False, "state": "succeeded"})])
    assert trigger.run_and_wait("https://svc", "s", SETTINGS, clock.sleep, clock) == 0
    assert len(calls) == 1


def test_health_mode(monkeypatch, capsys):
    clock = Clock()
    _script(monkeypatch, [(200, {"alerts": ["No pipeline run recorded for 30 hours"]})])
    assert trigger.health_check("https://svc", "s", SETTINGS, clock.sleep, clock) == 1
    assert "::error::No pipeline run recorded" in capsys.readouterr().out
    _script(monkeypatch, [(200, {"alerts": []})])
    assert trigger.health_check("https://svc", "s", SETTINGS, clock.sleep, clock) == 0


def test_settings_file_supplies_wait_limits():
    settings = trigger.load_trigger_settings(REPO_ROOT / "config" / "settings.yaml")
    assert settings["poll_limit_minutes"] == 45 and settings["start_wait_seconds"] == 180


@pytest.mark.parametrize("url, secret, expected", [
    ("", "s", "TRIGGER_URL is empty"),
    ("https://x.onrender.com", "", "TRIGGER_SECRET is empty"),
    ("my-service.onrender.com", "s", "must start with https://"),
])
def test_bad_trigger_settings_are_named_before_any_request(monkeypatch, capsys, url, secret, expected):
    calls = _script(monkeypatch, [])
    monkeypatch.setenv("TRIGGER_URL", url)
    monkeypatch.setenv("TRIGGER_SECRET", secret)
    assert trigger.main(["health"]) == 1
    assert expected in capsys.readouterr().out and calls == []


def test_whitespace_around_pasted_values_is_ignored(monkeypatch):
    calls = _script(monkeypatch, [(200, {"alerts": []})])
    monkeypatch.setenv("TRIGGER_URL", "  https://x.onrender.com/\n")
    monkeypatch.setenv("TRIGGER_SECRET", " s3cret\n")
    assert trigger.main(["health"]) == 0
    assert calls == [("POST", "https://x.onrender.com/health-check")]
