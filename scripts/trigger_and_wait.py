"""Wake the hosted service, start a run (or a health check), and wait for the result.

Used by the GitHub Actions workflows; also runnable by hand. Standard library plus PyYAML only.

  python scripts/trigger_and_wait.py run      # POST /runs, then poll GET /runs/{id}
  python scripts/trigger_and_wait.py health   # POST /health-check

Environment: TRIGGER_URL (service base URL), TRIGGER_SECRET (one of the service's TRIGGER_SECRETS).
Wait limits come from the `trigger` section of config/settings.yaml; flags override them for testing.
Exit code 0 = finished (succeeded or partial) or no health alerts; 1 = failed, interrupted, unreachable,
timed out, or health alerts. The secret is never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

FINISHED_OK = {"succeeded", "partial"}
FINISHED_BAD = {"failed", "interrupted"}
REPO_ROOT = Path(__file__).resolve().parents[1]


class Unreachable(Exception):
    """The service did not answer (asleep, waking, or down)."""


def http_json(method: str, url: str, secret: str, body: dict | None = None, timeout: float = 30) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {secret}", "Content-Type": "application/json", "User-Agent": "job-trigger/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode() or "{}"
            return response.status, json.loads(payload)
    except urllib.error.HTTPError as exc:
        if exc.code in (502, 503, 504):  # Render answers these while an instance is waking
            raise Unreachable(f"HTTP {exc.code}") from exc
        try:
            return exc.code, json.loads(exc.read().decode() or "{}")
        except ValueError:
            return exc.code, {}
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        raise Unreachable(type(exc).__name__) from exc


def call_with_wake_retry(method, url, secret, body, wait_seconds, retry_interval,
                         sleep=time.sleep, clock=time.monotonic):
    deadline = clock() + wait_seconds
    attempt = 0
    while True:
        attempt += 1
        try:
            return http_json(method, url, secret, body)
        except Unreachable as exc:
            if clock() >= deadline:
                raise Unreachable(f"no answer after {attempt} attempt(s) over {wait_seconds}s ({exc})") from exc
            print(f"service not answering yet ({exc}); attempt {attempt}, retrying in {retry_interval}s", flush=True)
            sleep(retry_interval)


def load_trigger_settings(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["trigger"]


def run_and_wait(base_url, secret, settings, sleep=time.sleep, clock=time.monotonic) -> int:
    status, body = call_with_wake_retry("POST", f"{base_url}/runs", secret, {"trigger_id": "github-cron"},
                                        settings["start_wait_seconds"], settings["start_retry_interval_seconds"],
                                        sleep, clock)
    if status == 401:
        print("::error::the service rejected the trigger secret (HTTP 401)")
        return 1
    if status not in (200, 202) or "run_id" not in body:
        print(f"::error::unexpected answer to start: HTTP {status} {body}")
        return 1
    run_id, state = body["run_id"], body.get("state")
    print(f"run {run_id}: started={body.get('started')} state={state} {body.get('reason', '')}".strip(), flush=True)

    deadline = clock() + settings["poll_limit_minutes"] * 60
    while state not in FINISHED_OK | FINISHED_BAD:
        if clock() >= deadline:
            print(f"::error::run {run_id} did not finish within {settings['poll_limit_minutes']} minutes")
            return 1
        sleep(settings["poll_interval_seconds"])
        try:
            status, body = call_with_wake_retry("GET", f"{base_url}/runs/{run_id}", secret, None,
                                                settings["start_wait_seconds"],
                                                settings["start_retry_interval_seconds"], sleep, clock)
        except Unreachable as exc:
            print(f"::error::lost contact with the service while run {run_id} was running ({exc})")
            return 1
        if status == 404:
            print(f"::error::the service no longer knows run {run_id} (it may have restarted)")
            return 1
        state = body.get("state")
        print(f"run {run_id}: {state}", flush=True)

    if state in FINISHED_BAD:
        print(f"::error::run {run_id} ended {state}: {body.get('summary') or body.get('error') or ''}")
        return 1
    if state == "partial":
        print(f"::warning::run {run_id} finished partial (some sources failed or were blocked)")
    print(f"run {run_id} finished {state}: {body.get('summary') or ''}")
    return 0


def health_check(base_url, secret, settings, sleep=time.sleep, clock=time.monotonic) -> int:
    status, body = call_with_wake_retry("POST", f"{base_url}/health-check", secret, None,
                                        settings["start_wait_seconds"], settings["start_retry_interval_seconds"],
                                        sleep, clock)
    if status != 200:
        print(f"::error::health check answered HTTP {status}")
        return 1
    alerts = body.get("alerts") or []
    for alert in alerts:
        print(f"::error::{alert}")
    if not alerts:
        print("health check passed")
    return 1 if alerts else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["run", "health"])
    parser.add_argument("--settings", default=str(REPO_ROOT / "config" / "settings.yaml"))
    parser.add_argument("--start-wait-seconds", type=int)
    parser.add_argument("--start-retry-interval-seconds", type=int)
    parser.add_argument("--poll-interval-seconds", type=int)
    parser.add_argument("--poll-limit-minutes", type=float)
    args = parser.parse_args(argv)

    base_url = os.environ.get("TRIGGER_URL", "").rstrip("/")
    secret = os.environ.get("TRIGGER_SECRET", "")
    if not base_url or not secret:
        print("::error::TRIGGER_URL and TRIGGER_SECRET must be set")
        return 1
    settings = load_trigger_settings(Path(args.settings))
    for key in ("start_wait_seconds", "start_retry_interval_seconds", "poll_interval_seconds", "poll_limit_minutes"):
        if getattr(args, key) is not None:
            settings[key] = getattr(args, key)
    try:
        if args.mode == "run":
            return run_and_wait(base_url, secret, settings)
        return health_check(base_url, secret, settings)
    except Unreachable as exc:
        print(f"::error::the service at {base_url} could not be reached: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
