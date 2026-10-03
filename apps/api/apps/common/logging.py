"""Logging helpers: request-id propagation and secret redaction."""
from __future__ import annotations

import contextvars
import logging
import re

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

# Patterns for values that must never appear in logs.
_REDACTIONS = [
    (re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key)([\"'\s:=]+)([^\s,\"'}]+)"),
     r"\1\2***REDACTED***"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"), "Bearer ***REDACTED***"),
    (re.compile(r"(?i)postgres(ql)?://[^\s]+"), "postgresql://***REDACTED***"),
]


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class RedactingFormatter(logging.Formatter):
    """Formatter that scrubs credentials from the final rendered message."""

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        return redact(rendered)


def redact(text: str) -> str:
    """Apply all redaction patterns to a string."""
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text
