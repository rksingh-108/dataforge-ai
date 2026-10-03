"""Publish execution lifecycle events to WebSocket subscribers."""
from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def publish_execution_event(execution) -> None:
    """Broadcast an execution update to its organization's subscribers.

    Called from synchronous code (request handlers, Celery tasks), hence
    ``async_to_sync``. Failures are the caller's to swallow; broadcasting must
    never break a request.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    group = f"org.{execution.organization_id}.executions"
    payload = {
        "type": "execution.updated",
        "execution_id": str(execution.id),
        "kind": execution.kind,
        "status": execution.status,
        "duration_ms": execution.duration_ms,
        "updated_at": execution.updated_at.isoformat() if execution.updated_at else None,
    }
    async_to_sync(channel_layer.group_send)(
        group, {"type": "execution_event", "payload": payload}
    )
