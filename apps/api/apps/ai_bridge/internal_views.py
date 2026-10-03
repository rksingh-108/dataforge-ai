"""Internal service endpoints consumed by the AI service.

These endpoints are *not* part of the public API. They require the shared service
token and an explicit organization scope, and they are the only way the AI
service can reach platform data.
"""
from __future__ import annotations

import logging
import uuid

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services import record_audit
from apps.common.service_auth import (
    ServiceTokenAuthentication,
    require_organization_scope,
)
from apps.datasources import selectors as datasource_selectors
from apps.documents import selectors as document_selectors

logger = logging.getLogger("apps.security.internal")


class _InternalView(APIView):
    authentication_classes = [ServiceTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_scope(self, request) -> uuid.UUID:
        return require_organization_scope(request)

    def get_caller(self, request):
        # Only used for logging/attribution; never treated as a user in authz.
        return request.headers.get("X-DataForge-User", "")


class DataSourceConnectionView(_InternalView):
    """Return decrypted connection settings for one data source.

    Access is scoped to the organization header and recorded in the audit log
    every single time, because this is the moment a credential crosses a service
    boundary.
    """

    def get(self, request, datasource_id):
        organization_id = self.get_scope(request)
        datasource = datasource_selectors.get_datasource(
            organization_id=organization_id, datasource_id=datasource_id
        )
        if datasource is None:
            return Response(
                {"error": {"code": "not_found", "message": "Data source not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        record_audit(
            organization=datasource.organization,
            actor=None,
            action="datasource.credential_accessed",
            target_type="datasource",
            target_id=str(datasource.id),
            metadata={"service": "ai-service", "caller_user": self.get_caller(request)},
        )
        return Response({"connection": datasource.connection_config(), "is_read_only": True})


class DataSourceSchemaView(_InternalView):
    """Return the cached schema for one data source, scoped to the organization.

    The AI service uses this to build the SQL allowlist, so it must never return
    tables from another tenant.
    """

    def get(self, request, datasource_id):
        organization_id = self.get_scope(request)
        datasource = datasource_selectors.get_datasource(
            organization_id=organization_id, datasource_id=datasource_id
        )
        if datasource is None:
            return Response(
                {"error": {"code": "not_found", "message": "Data source not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        tables = datasource_selectors.list_tables(datasource_id=datasource.id)
        return Response(
            {
                "datasource_id": str(datasource.id),
                "engine": datasource.engine,
                "tables": [
                    {
                        "schema": table.schema_name,
                        "name": table.table_name,
                        "columns": [
                            {
                                "column_name": column.column_name,
                                "data_type": column.data_type,
                                "is_nullable": column.is_nullable,
                                "is_primary_key": column.is_primary_key,
                            }
                            for column in table.columns.all()
                        ],
                    }
                    for table in tables
                ],
            }
        )


class DocumentSearchView(_InternalView):
    """pgvector similarity search scoped to a single organization."""

    def post(self, request):
        organization_id = self.get_scope(request)
        embedding = request.data.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            return Response(
                {"error": {"code": "bad_request", "message": "`embedding` must be a non-empty list."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            top_k = min(int(request.data.get("top_k", 5)), 50)
        except (TypeError, ValueError):
            top_k = 5

        document_ids = request.data.get("document_ids") or None
        if document_ids:
            document_ids = [uuid.UUID(str(d)) for d in document_ids]

        results = document_selectors.search_chunks(
            organization_id=organization_id,
            embedding=[float(v) for v in embedding],
            top_k=top_k,
            document_ids=document_ids,
        )
        return Response({"results": results})
