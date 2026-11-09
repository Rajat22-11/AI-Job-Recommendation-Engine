"""Notification channel interface, the ntfy.sh implementation, and the run summary message."""

from __future__ import annotations

import logging
from typing import Protocol

import httpx

from job_aggregator.domain.models import RunSummary

logger = logging.getLogger(__name__)
MAX_MESSAGE_CHARS = 3500


class Notifier(Protocol):
    def send(self, title: str, message: str, priority: str = "default", click_url: str | None = None) -> None: ...


class NoNotifier:
    """Used when `notifications.channel` is `none`."""

    def send(self, title: str, message: str, priority: str = "default", click_url: str | None = None) -> None:
        logger.info("notification (channel off): %s", title)


class NtfyNotifier:
    """Publishes to an ntfy.sh topic. The topic name is the secret, read from NTFY_TOPIC."""

    def __init__(self, server: str, topic: str, transport: httpx.BaseTransport | None = None,
                 timeout_seconds: float = 15) -> None:
        self._url = f"{server.rstrip('/')}/{topic}"
        self._client = httpx.Client(timeout=timeout_seconds, transport=transport)

    def send(self, title: str, message: str, priority: str = "default", click_url: str | None = None) -> None:
        headers = {"Title": title.encode("ascii", "ignore").decode(), "Priority": priority, "Tags": "briefcase"}
        if click_url:
            headers["Click"] = click_url
        response = self._client.post(self._url, content=message[:MAX_MESSAGE_CHARS].encode("utf-8"), headers=headers)
        response.raise_for_status()


def format_run_summary(summary: RunSummary, alerts: list[str]) -> tuple[str, str, str]:
    """Return (title, body, priority) for one run's notification."""
    problem_sources = [r for r in summary.source_records if r.status.value in ("failed", "blocked")]
    title = f"Job run: {summary.jobs_new} new job(s)"
    if summary.dry_run:
        title += " (dry run)"
    lines = [f"Status {summary.status.value}. Found {summary.jobs_found}, new {summary.jobs_new}, "
             f"discarded {summary.jobs_discarded}."]
    if summary.top_matches:
        lines.append("\nTop matches:")
        lines += [f"{m.fit_score}/5 {m.title} at {m.company}\n{m.apply_url}" for m in summary.top_matches]
    if problem_sources:
        lines.append("\nSource problems:")
        lines += [f"{r.source_id}: {r.status.value} ({r.message[:120]})" for r in problem_sources]
    if alerts:
        lines.append("\nHealth alerts:")
        lines += [f"- {alert}" for alert in alerts]
    priority = "high" if alerts or problem_sources else "default"
    return title, "\n".join(lines), priority


def send_notification_safely(notifier: Notifier, title: str, body: str, priority: str) -> str | None:
    """Send; return an error description instead of raising, so the run still completes."""
    try:
        notifier.send(title, body, priority)
        return None
    except Exception as exc:  # noqa: BLE001 - a notification failure must never fail the run
        logger.warning("notification failed: %s", type(exc).__name__)
        return f"notification failed: {type(exc).__name__}"


def ping_heartbeat(url: str | None, enabled: bool, transport: httpx.BaseTransport | None = None) -> bool:
    """Ping the heartbeat URL after a successful run; returns whether a ping was sent."""
    if not enabled or not url:
        return False
    try:
        with httpx.Client(timeout=10, transport=transport) as client:
            client.get(url).raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.warning("heartbeat ping failed: %s", type(exc).__name__)
        return False
