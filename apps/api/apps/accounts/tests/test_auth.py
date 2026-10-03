"""Authentication tests: login, refresh, logout, password change, current user."""
from __future__ import annotations

import pytest
from django.urls import reverse

from apps.analytics.models import AuditLog
from apps.common.rbac import Permission, permissions_for

pytestmark = pytest.mark.django_db

LOGIN = reverse("auth-login")
REFRESH = reverse("auth-refresh")
LOGOUT = reverse("auth-logout")
ME = reverse("current-user")
PASSWORD_CHANGE = reverse("auth-password-change")


def test_login_success_returns_tokens_and_memberships(api_client, user, organization):
    response = api_client.post(LOGIN, {"email": user.email, "password": "CorrectHorse9!"},
                               format="json")
    assert response.status_code == 200
    body = response.json()
    assert body["access"] and body["refresh"]
    assert body["user"]["email"] == user.email
    assert [m["organization_id"] for m in body["memberships"]] == [str(organization.id)]
    # The response must never contain password material.
    assert "password" not in response.content.decode().lower()


def test_login_is_case_insensitive_on_email(api_client, user):
    response = api_client.post(LOGIN, {"email": user.email.upper(), "password": "CorrectHorse9!"},
                               format="json")
    assert response.status_code == 200


def test_login_failure_is_401_and_audited(api_client, user):
    response = api_client.post(LOGIN, {"email": user.email, "password": "wrong-password"},
                               format="json")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert AuditLog.objects.filter(action="auth.login_failed").exists()


def test_me_requires_authentication(api_client):
    assert api_client.get(ME).status_code == 401


def test_me_returns_permissions(auth_client):
    response = auth_client.get(ME)
    assert response.status_code == 200
    body = response.json()
    perms = body["memberships"][0]["permissions"]
    assert Permission.ANALYST_QUERY.value in perms
    assert body["memberships"][0]["role"] == "owner"


def test_refresh_rotates_token(api_client, user):
    login = api_client.post(LOGIN, {"email": user.email, "password": "CorrectHorse9!"},
                            format="json").json()
    response = api_client.post(REFRESH, {"refresh": login["refresh"]}, format="json")
    assert response.status_code == 200
    assert response.json()["refresh"] != login["refresh"]


def test_logout_blacklists_refresh_token(api_client, user):
    login = api_client.post(LOGIN, {"email": user.email, "password": "CorrectHorse9!"},
                            format="json").json()
    client = api_client
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login['access']}")
    assert client.post(LOGOUT, {"refresh": login["refresh"]}, format="json").status_code == 205
    # Reusing the blacklisted refresh token must now fail.
    assert api_client.post(REFRESH, {"refresh": login["refresh"]}, format="json").status_code == 401


def test_password_change_requires_current_password(auth_client):
    response = auth_client.post(PASSWORD_CHANGE,
                                {"current_password": "nope", "new_password": "AnotherStrong1!"},
                                format="json")
    assert response.status_code == 400


def test_password_change_revokes_refresh_tokens(api_client, user):
    login = api_client.post(LOGIN, {"email": user.email, "password": "CorrectHorse9!"},
                            format="json").json()
    client = api_client
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login['access']}")
    response = client.post(PASSWORD_CHANGE,
                           {"current_password": "CorrectHorse9!", "new_password": "AnotherStrong1!"},
                           format="json")
    assert response.status_code == 200
    assert response.json()["revoked_refresh_tokens"] >= 1
    assert api_client.post(REFRESH, {"refresh": login["refresh"]}, format="json").status_code == 401


def test_viewer_permissions_are_read_only():
    perms = permissions_for("viewer")
    assert Permission.ANALYST_QUERY.value not in perms
    assert Permission.DATASOURCE_MANAGE.value not in perms
    assert Permission.DOCUMENT_VIEW.value in perms


def test_unknown_role_grants_nothing():
    assert permissions_for("super-duper-admin") == frozenset()
