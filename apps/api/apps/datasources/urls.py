from django.urls import path

from apps.datasources.views import (
    DataSourceDetailView,
    DataSourceListCreateView,
    DataSourceSchemaSyncView,
    DataSourceSchemaView,
    DataSourceTestView,
)

urlpatterns = [
    path("", DataSourceListCreateView.as_view(), name="datasource-list"),
    path("<uuid:datasource_id>/", DataSourceDetailView.as_view(), name="datasource-detail"),
    path("<uuid:datasource_id>/test/", DataSourceTestView.as_view(), name="datasource-test"),
    path("<uuid:datasource_id>/schema/", DataSourceSchemaView.as_view(), name="datasource-schema"),
    path("<uuid:datasource_id>/sync/", DataSourceSchemaSyncView.as_view(),
         name="datasource-schema-sync"),
]
