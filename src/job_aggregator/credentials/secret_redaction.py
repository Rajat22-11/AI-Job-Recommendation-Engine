"""Keep secret values out of logs, notifications, database rows and error messages."""

from __future__ import annotations

import logging
import threading

_lock = threading.Lock()
_secrets: dict[str, str] = {}


def register_secret(value: str, label: str) -> None:
    """Remember a secret so `redact_secrets` replaces it with `label` wherever it appears."""
    if value and len(value) >= 4:
        with _lock:
            _secrets[value] = label


def clear_registered_secrets() -> None:
    """Forget every registered secret (used by tests)."""
    with _lock:
        _secrets.clear()


def redact_secrets(text: str) -> str:
    """Return `text` with every registered secret replaced by its label."""
    if not text:
        return text
    with _lock:
        items = sorted(_secrets.items(), key=lambda item: len(item[0]), reverse=True)
    for value, label in items:
        if value in text:
            text = text.replace(value, f"<{label}>")
    return text


class SecretRedactingFilter(logging.Filter):
    """Logging filter that redacts the formatted message and any exception text."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_secrets(record.getMessage())
        record.args = None
        if record.exc_info:
            record.exc_text = redact_secrets(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        return True


def install_secret_redaction(logger: logging.Logger | None = None) -> None:
    """Attach the redacting filter to every handler of `logger` (root by default)."""
    target = logger or logging.getLogger()
    for handler in target.handlers:
        if not any(isinstance(f, SecretRedactingFilter) for f in handler.filters):
            handler.addFilter(SecretRedactingFilter())
