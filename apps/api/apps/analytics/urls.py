from django.urls import path

from apps.analytics.views import (
    AuditLogListView,
    ExecutionDetailView,
    ExecutionListView,
    InsightsView,
)

urlpatterns = [
    path("executions/", ExecutionListView.as_view(), name="execution-list"),
    path("executions/<uuid:execution_id>/", ExecutionDetailView.as_view(),
         name="execution-detail"),
    path("audit-logs/", AuditLogListView.as_view(), name="audit-log-list"),
    path("insights/", InsightsView.as_view(), name="insights"),
]
