"""Internal (service-to-service) endpoint security tests."""
from __future__ import annotations

import pytest

from apps.analytics.models import AuditLog
from apps.common.rbac import Role
from apps.datasources.models import DataSource
from apps.documents.models import Document, DocumentChunk, DocumentStatus
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db

TOKEN = "test-internal-service-token"


@pytest.fixture
def datasource(organization, user):
    ds = DataSource.objects.create(
        organization=organization,
        name="Warehouse",
        engine="postgresql",
        host="db.example.com",
        port=5432,
        database_name="analytics",
        username="readonly",
        created_by=user,
    )
    ds.set_password("sup3r-secret")
    ds.save()
    return ds


def _auth(org_id=None, token=TOKEN):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    if org_id is not None:
        headers["HTTP_X_DATAFORGE_ORG"] = str(org_id)
    return headers


def _connection_url(datasource_id):
    return f"/internal/datasources/{datasource_id}/connection"


def test_missing_service_token_is_rejected(api_client, datasource):
    response = api_client.get(_connection_url(datasource.id),
                              HTTP_X_DATAFORGE_ORG=str(datasource.organization_id))
    assert response.status_code in {401, 403}


def test_wrong_service_token_is_rejected(api_client, datasource):
    response = api_client.get(_connection_url(datasource.id),
                              **_auth(datasource.organization_id, token="not-the-token"))
    assert response.status_code in {401, 403}


def test_missing_org_scope_is_rejected(api_client, datasource):
    response = api_client.get(_connection_url(datasource.id), **_auth())
    assert response.status_code == 400


def test_valid_service_token_returns_connection_config(api_client, datasource):
    response = api_client.get(_connection_url(datasource.id),
                              **_auth(datasource.organization_id))
    assert response.status_code == 200
    config = response.json()["connection"]
    assert config["password"] == "sup3r-secret"
    assert config["host"] == "db.example.com"


def test_credential_access_is_audited(api_client, datasource):
    api_client.get(_connection_url(datasource.id), **_auth(datasource.organization_id))
    entry = AuditLog.objects.get(action="datasource.credential_accessed")
    assert entry.organization_id == datasource.organization_id
    # The audit entry must not contain the secret itself.
    assert "sup3r-secret" not in str(entry.metadata)


def test_service_cannot_reach_another_tenant_datasource(api_client, datasource, other_user):
    foreign = Organization.objects.create(name="Globex", slug="globex", created_by=other_user)
    Membership.objects.create(organization=foreign, user=other_user, role=Role.OWNER.value)
    response = api_client.get(_connection_url(datasource.id), **_auth(foreign.id))
    assert response.status_code == 404


def test_document_search_requires_service_token(api_client, organization):
    response = api_client.post("/internal/documents/search", {"embedding": [0.1] * 1536},
                               format="json", HTTP_X_DATAFORGE_ORG=str(organization.id))
    assert response.status_code in {401, 403}


def test_document_search_is_tenant_scoped(api_client, organization, user, other_user):
    def make_doc(org, owner, title, content):
        doc = Document.objects.create(
            organization=org, title=title, original_filename=f"{title}.txt",
            content_type="text/plain", size_bytes=4, status=DocumentStatus.READY, uploaded_by=owner,
        )
        DocumentChunk.objects.create(
            document=doc, organization=org, chunk_index=0, content=content,
            char_count=len(content), embedding=[1.0] + [0.0] * 1535,
        )
        return doc

    make_doc(organization, user, "mine", "my private chunk")
    foreign = Organization.objects.create(name="Globex", slug="globex", created_by=other_user)
    Membership.objects.create(organization=foreign, user=other_user, role=Role.OWNER.value)
    make_doc(foreign, other_user, "theirs", "their private chunk")

    response = api_client.post(
        "/internal/documents/search",
        {"embedding": [1.0] + [0.0] * 1535, "top_k": 5},
        format="json",
        **_auth(organization.id),
    )
    assert response.status_code == 200
    assert [r["content"] for r in response.json()["results"]] == ["my private chunk"]
