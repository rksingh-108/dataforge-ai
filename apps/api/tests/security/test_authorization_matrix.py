"""Authorization matrix.

The point of this suite is breadth: for each role and each write endpoint we
assert the *exact* expected outcome. If a permission is added to a role by
accident, this fails.
"""
from __future__ import annotations

from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.common.rbac import Role

pytestmark = pytest.mark.django_db


def _user_with_role(organization, role, make_member):
    _member, client = make_member(organization, role, email=f"matrix-{role}@example.com")
    return client


def _urls(org_id):
    return {
        "datasource_list": reverse("datasource-list", kwargs={"org_id": org_id}),
        "document_list": reverse("document-list", kwargs={"org_id": org_id}),
        "analyst_query": reverse("analyst-query", kwargs={"org_id": org_id}),
        "execution_list": reverse("execution-list", kwargs={"org_id": org_id}),
        "audit_list": reverse("audit-log-list", kwargs={"org_id": org_id}),
        "member_list": reverse("organization-members", kwargs={"org_id": org_id}),
    }


DATASOURCE_PAYLOAD = {
    "name": "Report DB",
    "engine": "postgresql",
    "host": "db.example.com",
    "port": 5432,
    "database_name": "reporting",
    "username": "ro",
    "password": "pw",
}


@pytest.mark.parametrize(
    "role,method,key,expected",
    [
        # Read endpoints: everyone in the organization can read.
        (Role.VIEWER.value, "get", "datasource_list", 200),
        (Role.ANALYST.value, "get", "datasource_list", 200),
        (Role.ADMIN.value, "get", "datasource_list", 200),
        (Role.OWNER.value, "get", "datasource_list", 200),
        (Role.VIEWER.value, "get", "execution_list", 200),
        (Role.ANALYST.value, "get", "execution_list", 200),
        # Managing data sources: admin+ only.
        (Role.VIEWER.value, "post", "datasource_list", 403),
        (Role.ANALYST.value, "post", "datasource_list", 403),
        (Role.ADMIN.value, "post", "datasource_list", 201),
        (Role.OWNER.value, "post", "datasource_list", 201),
        # Audit logs: admin+ only.
        (Role.VIEWER.value, "get", "audit_list", 403),
        (Role.ANALYST.value, "get", "audit_list", 403),
        (Role.ADMIN.value, "get", "audit_list", 200),
        (Role.OWNER.value, "get", "audit_list", 200),
        # Member management: admin+ only.
        (Role.VIEWER.value, "get", "member_list", 200),
        (Role.VIEWER.value, "post", "member_list", 403),
        (Role.ANALYST.value, "post", "member_list", 403),
        # Running the analyst: analyst+ only.
        (Role.VIEWER.value, "post", "analyst_query", 403),
    ],
)
def test_role_matrix(role, method, key, expected, organization, make_member, monkeypatch):
    client = _user_with_role(organization, role, make_member)
    urls = _urls(organization.id)

    if method == "post":
        if key == "datasource_list":
            with mock.patch("apps.datasources.services.validate_host"):
                response = client.post(urls[key], DATASOURCE_PAYLOAD, format="json")
        elif key == "analyst_query":
            with mock.patch("apps.ai_bridge.services.AIServiceClient") as client_cls:
                client_cls.return_value.run_agent.return_value = {
                    "answer": "ok", "steps": [], "provider": "p", "model": "m", "total_tokens": 1
                }
                response = client.post(urls[key], {"question": "Anything?"}, format="json")
        elif key == "member_list":
            response = client.post(urls[key], {"email": "someone@example.com", "role": "viewer"},
                                   format="json")
        else:  # pragma: no cover - defensive
            raise AssertionError(f"unhandled post endpoint {key}")
    else:
        response = client.get(urls[key])

    assert response.status_code == expected, (
        f"{role} {method.upper()} {key} -> {response.status_code}, expected {expected}"
    )


def test_document_upload_roles(organization, make_member):
    for role, expected in [
        (Role.VIEWER.value, 403),
        (Role.ANALYST.value, 201),
        (Role.ADMIN.value, 201),
    ]:
        client = _user_with_role(organization, role, make_member)
        # Unique content per role: identical content would trip the per-org
        # duplicate-document rule and mask the authorization result.
        payload = f"authorization matrix test document for {role}\n".encode() * 3
        upload = SimpleUploadedFile(f"{role}.txt", payload, content_type="text/plain")
        with mock.patch("apps.documents.services.enqueue_processing"):
            response = client.post(
                reverse("document-list", kwargs={"org_id": organization.id}),
                {"file": upload},
                format="multipart",
            )
        assert response.status_code == expected, f"{role} upload -> {response.status_code}"


def test_unknown_role_grants_nothing():
    from apps.common.rbac import permissions_for

    assert permissions_for("root") == frozenset()
    assert permissions_for("") == frozenset()
