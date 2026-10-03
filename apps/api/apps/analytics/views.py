"""Execution history, audit log and insights endpoints."""
from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics import selectors
from apps.analytics.models import Execution, ExecutionStatus
from apps.analytics.serializers import (
    AuditLogSerializer,
    ExecutionDetailSerializer,
    ExecutionSerializer,
)
from apps.common.exceptions import NotFound
from apps.common.permissions import require_organization, require_permission
from apps.common.rbac import Permission


class ExecutionListView(generics.ListAPIView):
    permission_classes = [require_permission(Permission.EXECUTION_VIEW)]
    serializer_class = ExecutionSerializer
    filterset_fields = ["kind", "status"]

    def get_queryset(self):
        # Scope comes from the verified membership, never the raw URL/query value.
        return selectors.list_executions(
            organization_id=require_organization(self.request).id,
            kind=self.request.query_params.get("kind"),
            status=self.request.query_params.get("status"),
        )


class ExecutionDetailView(generics.RetrieveAPIView):
    permission_classes = [require_permission(Permission.EXECUTION_VIEW)]
    serializer_class = ExecutionDetailSerializer

    def get_object(self):
        execution = selectors.get_execution(
            organization_id=require_organization(self.request).id,
            execution_id=self.kwargs["execution_id"],
        )
        if execution is None:
            raise NotFound("Execution not found.")
        return execution


class AuditLogListView(generics.ListAPIView):
    permission_classes = [require_permission(Permission.AUDIT_VIEW)]
    serializer_class = AuditLogSerializer
    filterset_fields = ["action"]

    def get_queryset(self):
        return selectors.list_audit_logs(
            organization_id=require_organization(self.request).id,
            action=self.request.query_params.get("action"),
        )


class InsightsView(APIView):
    """Aggregate, org-scoped metrics for the dashboard.

    These are real aggregates over recorded executions — not synthetic data.
    """

    permission_classes = [require_permission(Permission.EXECUTION_VIEW)]

    def get(self, request, org_id):
        organization = require_organization(request)
        base = Execution.objects.filter(organization_id=organization.id)
        totals = base.aggregate(
            total=Count("id"),
            succeeded=Count("id", filter=Q(status=ExecutionStatus.SUCCEEDED)),
            failed=Count("id", filter=Q(status=ExecutionStatus.FAILED)),
            running=Count("id", filter=Q(status=ExecutionStatus.RUNNING)),
        )
        tools = (
            Execution.objects.filter(organization_id=organization.id)
            .values("steps__tool_name")
            .exclude(steps__tool_name="")
            .annotate(count=Count("steps__tool_name"))
            .order_by("-count")[:5]
        )
        total = totals["total"] or 0
        success_rate = round((totals["succeeded"] / total) * 100, 1) if total else 0.0
        return Response(
            {
                "executions": {
                    "total": total,
                    "succeeded": totals["succeeded"],
                    "failed": totals["failed"],
                    "running": totals["running"],
                    "success_rate_percent": success_rate,
                },
                "top_tools": [
                    {"tool": row["steps__tool_name"], "count": row["count"]} for row in tools
                ],
            }
        )
