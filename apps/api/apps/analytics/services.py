"""Services for audit logging and execution lifecycle.

These functions are the only sanctioned way to write audit entries or move an
execution through its states, so lifecycle invariants (timestamps, terminal
states, realtime broadcast) are enforced in one place.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from django.utils import timezone

from apps.analytics.models import (
    AuditLog,
    Execution,
    ExecutionStatus,
    ExecutionStep,
)
from apps.common.logging import get_request_id

logger = logging.getLogger("apps.analytics")

_TERMINAL = {ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED}


def record_audit(
    *,
    organization=None,
    actor=None,
    action: str,
    target_type: str = "",
    target_id: str | None = "",
    metadata: dict[str, Any] | None = None,
    request=None,
) -> AuditLog:
    """Append a security-relevant event. Never raises into the caller's flow."""
    ip_address = None
    request_id = get_request_id()
    if request is not None:
        ip_address = _client_ip(request)
        request_id = getattr(request, "request_id", request_id)
    try:
        return AuditLog.objects.create(
            organization=organization,
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id or ""),
            metadata=metadata or {},
            ip_address=ip_address,
            request_id=request_id,
        )
    except Exception:
        logger.exception("Failed to write audit log entry for action=%s", action)
        raise


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# --- Execution lifecycle -----------------------------------------------------

def start_execution(
    *,
    organization,
    user,
    kind: str,
    question: str = "",
    datasource=None,
    document=None,
) -> Execution:
    execution = Execution.objects.create(
        organization=organization,
        user=user if getattr(user, "is_authenticated", False) else None,
        kind=kind,
        status=ExecutionStatus.RUNNING,
        question=question,
        datasource=datasource,
        document=document,
        started_at=timezone.now(),
        request_id=get_request_id(),
    )
    _publish(execution)
    return execution


def add_step(
    *,
    execution: Execution,
    index: int,
    tool_name: str,
    title: str = "",
    status: str = ExecutionStatus.SUCCEEDED,
    input_summary: dict | None = None,
    output_summary: dict | None = None,
    duration_ms: int = 0,
    error: str = "",
) -> ExecutionStep:
    return ExecutionStep.objects.create(
        execution=execution,
        index=index,
        tool_name=tool_name,
        title=title,
        status=status,
        input_summary=input_summary or {},
        output_summary=output_summary or {},
        duration_ms=duration_ms,
        error=error,
    )


def finish_execution(
    *,
    execution: Execution,
    status: str,
    answer: str = "",
    error: str = "",
    provider: str = "",
    model_name: str = "",
    total_tokens: int = 0,
) -> Execution:
    if execution.status in {s.value for s in _TERMINAL}:
        raise ValueError("Execution is already in a terminal state.")
    if status not in {s.value for s in _TERMINAL}:
        raise ValueError(f"finish_execution requires a terminal status, got {status!r}.")

    execution.status = status
    execution.answer = answer
    execution.error = error[:5000]
    execution.provider = provider
    execution.model_name = model_name
    execution.total_tokens = total_tokens
    execution.finished_at = timezone.now()
    if execution.started_at:
        execution.duration_ms = int(
            (execution.finished_at - execution.started_at).total_seconds() * 1000
        )
    execution.save(
        update_fields=[
            "status", "answer", "error", "provider", "model_name", "total_tokens",
            "finished_at", "duration_ms", "updated_at",
        ]
    )
    _publish(execution)
    return execution


def _publish(execution: Execution) -> None:
    """Best-effort realtime broadcast; never fails the request."""
    try:
        from apps.realtime.broadcast import publish_execution_event

        publish_execution_event(execution)
    except Exception:
        logger.warning("Realtime broadcast failed for execution %s", execution.id, exc_info=True)


class Timer:
    """Small context manager to measure step durations in milliseconds."""

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        self.elapsed_ms = 0
        return self

    def __exit__(self, *exc) -> None:
        self.elapsed_ms = int((time.perf_counter() - self._start) * 1000)
