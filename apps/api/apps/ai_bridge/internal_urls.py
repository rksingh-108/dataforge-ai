from django.urls import path

from apps.ai_bridge.internal_views import (
    DataSourceConnectionView,
    DataSourceSchemaView,
    DocumentSearchView,
)

urlpatterns = [
    path(
        "datasources/<uuid:datasource_id>/connection",
        DataSourceConnectionView.as_view(),
        name="internal-datasource-connection",
    ),
    path(
        "datasources/<uuid:datasource_id>/schema",
        DataSourceSchemaView.as_view(),
        name="internal-datasource-schema",
    ),
    path("documents/search", DocumentSearchView.as_view(), name="internal-document-search"),
]
