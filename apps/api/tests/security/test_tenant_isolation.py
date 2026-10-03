"""Tenant isolation: a member of one organization must never reach another's data.

These tests exercise the *whole* API surface rather than a single app, because a
leak in any one endpoint is equally fatal.
"""
from __future__ import annotations

import pytest
from django.urls import reverse

from apps.common.rbac import Role
from apps.datasources.models import DataSource
from apps.documents.models import Document, DocumentStatus
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def two_orgs(user, other_user):
    """Acme (user, owner) and Globex (other_user, owner), each with a data source."""
    acme = Organization.objects.create(name="Acme", slug="acme", created_by=user)
    Membership.objects.create(organization=acme, user=user, role=Role.OWNER.value)
    globex = Organization.objects.create(name="Globex", slug="globex", created_by=other_user)
    Membership.objects.create(organization=globex, user=other_user, role=Role.OWNER.value)

    acme_source = DataSource.objects.create(
        organization=acme, name="Acme DB", engine="postgresql", host="db.example.com",
        port=5432, database_name="acme", username="ro", password_encrypted=b"x", created_by=user,
    )
    globex_source = DataSource.objects.create(
        organization=globex, name="Globex DB", engine="postgresql", host="db.example.com",
        port=5432, database_name="globex", username="ro", password_encrypted=b"x",
        created_by=other_user,
    )
    Document.objects.create(
        organization=globex, title="Globex secret", original_filename="s.txt",
        content_type="text/plain", size_bytes=10, status=DocumentStatus.READY,
        uploaded_by=other_user,
    )
    return acme, globex, acme_source, globex_source


def test_organization_list_is_scoped(two_orgs, client_for, user):
    acme, globex, *_ = two_orgs
    response = client_for(user).get(reverse("organization-list"))
    assert [row["id"] for row in response.json()] == [str(acme.id)]
    assert str(globex.id) not in response.text


def test_foreign_organization_is_not_found(two_orgs, client_for, user):
    _acme, globex, *_ = two_orgs
    response = client_for(user).get(reverse("organization-detail", kwargs={"org_id": globex.id}))
    # 404 rather than 403: existence of another tenant's org is not disclosed.
    assert response.status_code == 404


def test_foreign_datasource_list_is_not_found(two_orgs, client_for, user):
    """Org-scoped routes answer 404 for a non-member.

    The organization id is part of the path, so refusing the whole route (rather
    than returning an empty list) also avoids confirming that the organization
    exists. The response must not leak any of its data either way.
    """
    _acme, globex, *_ = two_orgs
    response = client_for(user).get(reverse("datasource-list", kwargs={"org_id": globex.id}))
    assert response.status_code == 404
    assert "Globex DB" not in response.content.decode()


def test_foreign_datasource_detail_is_not_found(two_orgs, client_for, user):
    _acme, globex, _acme_source, globex_source = two_orgs
    response = client_for(user).get(
        reverse("datasource-detail", kwargs={"org_id": globex.id,
                                             "datasource_id": globex_source.id})
    )
    assert response.status_code == 404


def test_foreign_document_is_not_reachable(two_orgs, client_for, user):
    _acme, globex, *_ = two_orgs
    response = client_for(user).get(reverse("document-list", kwargs={"org_id": globex.id}))
    assert response.status_code == 404
    assert "Globex secret" not in response.content.decode()


def test_cannot_create_resources_in_another_org(two_orgs, client_for, user):
    _acme, globex, *_ = two_orgs
    response = client_for(user).post(
        reverse("datasource-list", kwargs={"org_id": globex.id}),
        {"name": "Injected", "engine": "postgresql", "host": "db.example.com", "port": 5432,
         "database_name": "x", "username": "u", "password": "p"},
        format="json",
    )
    assert response.status_code == 404
    assert not DataSource.objects.filter(organization=globex, name="Injected").exists()


def test_internal_endpoint_rejects_foreign_org_scope(two_orgs, api_client):
    _acme, globex, acme_source, _globex_source = two_orgs
    response = api_client.get(
        f"/internal/datasources/{acme_source.id}/connection",
        HTTP_AUTHORIZATION="Bearer test-internal-service-token",
        HTTP_X_DATAFORGE_ORG=str(globex.id),
    )
    assert response.status_code == 404


def test_internal_schema_endpoint_is_scoped(two_orgs, api_client):
    _acme, globex, acme_source, _globex_source = two_orgs
    response = api_client.get(
        f"/internal/datasources/{acme_source.id}/schema",
        HTTP_AUTHORIZATION="Bearer test-internal-service-token",
        HTTP_X_DATAFORGE_ORG=str(globex.id),
    )
    assert response.status_code == 404
