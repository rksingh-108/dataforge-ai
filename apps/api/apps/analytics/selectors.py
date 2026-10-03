"""Selectors for execution history and audit logs (always org-scoped)."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db.models import QuerySet

if TYPE_CHECKING:
    pass


def list_executions(*, organization_id: uuid.UUID, kind: str | None = None,
                    status: str | None = None) -> QuerySet:
    from apps.analytics.models import Execution

    qs = Execution.objects.filter(organization_id=organization_id).select_related(
        "user", "datasource", "document"
    )
    if kind:
        qs = qs.filter(kind=kind)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def get_execution(*, organization_id: uuid.UUID, execution_id: uuid.UUID):
    from apps.analytics.models import Execution

    return (
        Execution.objects.filter(id=execution_id, organization_id=organization_id)
        .select_related("user", "datasource", "document")
        .prefetch_related("steps")
        .first()
    )


def list_audit_logs(*, organization_id: uuid.UUID, action: str | None = None) -> QuerySet:
    from apps.analytics.models import AuditLog

    qs = AuditLog.objects.filter(organization_id=organization_id).select_related("actor")
    if action:
        qs = qs.filter(action=action)
    return qs.order_by("-created_at")
