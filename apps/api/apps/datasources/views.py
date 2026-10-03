"""Data source endpoints."""
from __future__ import annotations

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import NotFound
from apps.common.permissions import require_organization, require_permission
from apps.common.rbac import Permission
from apps.datasources import selectors, services
from apps.datasources.serializers import (
    DataSourceCreateSerializer,
    DataSourceSerializer,
    DataSourceUpdateSerializer,
    SchemaTableSerializer,
)


def _get_datasource_or_404(request, datasource_id):
    datasource = selectors.get_datasource(
        organization_id=require_organization(request).id, datasource_id=datasource_id
    )
    if datasource is None:
        # 404 (not 403) so cross-tenant ids are not distinguishable from missing.
        raise NotFound("Data source not found.")
    return datasource


class DataSourceListCreateView(generics.ListCreateAPIView):
    serializer_class = DataSourceSerializer
    permission_classes = [require_permission(Permission.DATASOURCE_VIEW)]

    def get_permissions(self):
        if self.request.method == "POST":
            return [require_permission(Permission.DATASOURCE_MANAGE)()]
        return super().get_permissions()

    def get_queryset(self):
        # Scope comes from the verified membership, never the raw URL value.
        return selectors.list_datasources(
            organization_id=require_organization(self.request).id
        )

    def create(self, request, *args, **kwargs):
        payload = DataSourceCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        datasource = services.create_datasource(
            organization=request.membership.organization,
            actor=request.user,
            **payload.validated_data,
        )
        return Response(DataSourceSerializer(datasource).data, status=status.HTTP_201_CREATED)


class DataSourceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DataSourceSerializer
    permission_classes = [require_permission(Permission.DATASOURCE_MANAGE)]
    http_method_names = ["get", "patch", "delete"]

    def get_permissions(self):
        if self.request.method == "GET":
            return [require_permission(Permission.DATASOURCE_VIEW)()]
        return super().get_permissions()

    def get_object(self):
        return _get_datasource_or_404(self.request, self.kwargs["datasource_id"])

    def update(self, request, *args, **kwargs):
        payload = DataSourceUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        datasource = services.update_datasource(
            datasource=self.get_object(), actor=request.user, **payload.validated_data
        )
        return Response(DataSourceSerializer(datasource).data)

    def destroy(self, request, *args, **kwargs):
        services.delete_datasource(datasource=self.get_object(), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DataSourceTestView(APIView):
    permission_classes = [require_permission(Permission.DATASOURCE_MANAGE)]

    def post(self, request, org_id, datasource_id):
        datasource = _get_datasource_or_404(request, datasource_id)
        result = services.test_connection(datasource=datasource, actor=request.user)
        return Response(
            {"ok": bool(result.get("ok")), "server_version": result.get("server_version", ""),
             "error": result.get("error", "")},
        )


class DataSourceSchemaView(generics.ListAPIView):
    serializer_class = SchemaTableSerializer
    permission_classes = [require_permission(Permission.DATASOURCE_VIEW)]
    pagination_class = None

    def get_queryset(self):
        _get_datasource_or_404(self.request, self.kwargs["datasource_id"])
        return selectors.list_tables(datasource_id=self.kwargs["datasource_id"])


class DataSourceSchemaSyncView(APIView):
    permission_classes = [require_permission(Permission.DATASOURCE_MANAGE)]

    def post(self, request, org_id, datasource_id):
        datasource = _get_datasource_or_404(request, datasource_id)
        result = services.sync_schema(datasource=datasource, actor=request.user)
        return Response(result, status=status.HTTP_200_OK)
