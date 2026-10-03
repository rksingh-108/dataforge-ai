"""Public API v1 route table.

Org-scoped resources are nested under `/orgs/<org_id>/...`. Tenant isolation is
enforced by `apps.common.permissions.OrganizationPermission`, which resolves the
caller's membership before any view code runs.
"""
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from apps.accounts.views import (
    CurrentUserView,
    LoginView,
    LogoutView,
    PasswordChangeView,
)

urlpatterns = [
    # --- Auth ---------------------------------------------------------------
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/verify/", TokenVerifyView.as_view(), name="auth-verify"),
    path("auth/password/change/", PasswordChangeView.as_view(), name="auth-password-change"),

    # --- Current user -------------------------------------------------------
    path("me/", CurrentUserView.as_view(), name="current-user"),

    # --- Organization-scoped resources --------------------------------------
    path("orgs/", include("apps.organizations.urls")),
    path("orgs/<uuid:org_id>/datasources/", include("apps.datasources.urls")),
    path("orgs/<uuid:org_id>/documents/", include("apps.documents.urls")),
    path("orgs/<uuid:org_id>/analytics/", include("apps.analytics.urls")),
    path("orgs/<uuid:org_id>/analyst/", include("apps.ai_bridge.urls")),
]
