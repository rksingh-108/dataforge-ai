"""Public analyst endpoint (org-scoped)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_bridge import services
from apps.analytics.serializers import AnalystQuerySerializer, ExecutionDetailSerializer
from apps.common.permissions import require_organization, require_permission
from apps.common.rbac import Permission


class AnalystQueryView(APIView):
    """`POST /api/v1/orgs/<org_id>/analyst/query/` — run the AI analyst."""

    permission_classes = [require_permission(Permission.ANALYST_QUERY)]
    throttle_scope = "analyst"

    def post(self, request, org_id):
        payload = AnalystQuerySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        execution = services.run_analyst_query(
            organization=require_organization(request),
            user=request.user,
            question=payload.validated_data["question"],
            datasource_ids=payload.validated_data.get("datasource_ids"),
            use_documents=payload.validated_data.get("use_documents", True),
            request_id=getattr(request, "request_id", None),
        )
        return Response(ExecutionDetailSerializer(execution).data, status=status.HTTP_201_CREATED)
