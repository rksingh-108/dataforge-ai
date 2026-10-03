"""Tenant-scope resolution: which organization a request operates on.

The rule under test: the tenant is derived from the **URL route plus a verified
membership**, and from nothing the client can set on its own. This locks down the
previously-open risk where a client-supplied ``X-Organization-Id`` header acted as
an authorization fallback (tracked as S12 / VM-8).

Every case here exercises the real permission classes, selectors and views — no
authorization logic is mocked. The only patch is the outbound AI client, because
no AI service runs in tests.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from apps.analytics.models import AuditLog, Execution, ExecutionKind, ExecutionStatus
from apps.common.exceptions import NotFound
from apps.common.permissions import OrganizationAccess, require_organization
from apps.common.rbac import Role
from apps.datasources.models import DataSource
from apps.documents.models import Document, DocumentStatus
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db

SERVICE_TOKEN = "test-internal-service-token"

DATASOURCE_PAYLOAD = {
    "name": "Injected DB",
    "engine": "postgresql",
    "host": "db.example.com",
    "port": 5432,
    "database_name": "injected",
    "username": "ro",
    "password": "pw",
}


def _urls(org_id):
    return {
        "datasource_list": reverse("datasource-list", kwargs={"org_id": org_id}),
        "document_list": reverse("document-list", kwargs={"org_id": org_id}),
        "execution_list": reverse("execution-list", kwargs={"org_id": org_id}),
        "audit_list": reverse("audit-log-list", kwargs={"org_id": org_id}),
        "insights": reverse("insights", kwargs={"org_id": org_id}),
        "member_list": reverse("organization-members", kwargs={"org_id": org_id}),
    }


@pytest.fixture
def tenants(user, other_user):
    """Acme (user = owner) and Globex (other_user = owner), each with real data."""
    acme = Organization.objects.create(name="Acme", slug="acme-scope", created_by=user)
    Membership.objects.create(organization=acme, user=user, role=Role.OWNER.value)
    globex = Organization.objects.create(name="Globex", slug="globex-scope", created_by=other_user)
    Membership.objects.create(organization=globex, user=other_user, role=Role.OWNER.value)

    acme_source = DataSource.objects.create(
        organization=acme, name="Acme DB", engine="postgresql", host="db.example.com",
        port=5432, database_name="acme", username="ro", created_by=user,
    )
    acme_source.set_password("acme-secret")
    acme_source.save(update_fields=["password_encrypted"])

    globex_source = DataSource.objects.create(
        organization=globex, name="Globex DB", engine="postgresql", host="db.example.com",
        port=5432, database_name="globex", username="ro", created_by=other_user,
    )
    globex_source.set_password("globex-secret")
    globex_source.save(update_fields=["password_encrypted"])
    globex_document = Document.objects.create(
        organization=globex, title="Globex secret", original_filename="s.txt",
        content_type="text/plain", size_bytes=10, status=DocumentStatus.READY,
        uploaded_by=other_user,
    )
    Execution.objects.create(
        organization=acme, kind=ExecutionKind.ANALYST_QUERY,
        status=ExecutionStatus.SUCCEEDED, question="Acme question",
    )
    globex_execution = Execution.objects.create(
        organization=globex, kind=ExecutionKind.ANALYST_QUERY,
        status=ExecutionStatus.SUCCEEDED, question="Globex secret question",
    )
    AuditLog.objects.create(organization=acme, action="acme.event")
    AuditLog.objects.create(organization=globex, action="globex.secret.event")

    return SimpleNamespace(
        acme=acme, globex=globex, acme_source=acme_source, globex_source=globex_source,
        globex_document=globex_document, globex_execution=globex_execution,
    )


# --- A / B / D: header cannot move or widen the tenant ------------------------

def test_forged_header_cannot_switch_tenant_data(tenants, client_for, user):
    """A member of Acme sending Globex's id in the header still sees only Acme."""
    response = client_for(user).get(
        _urls(tenants.acme.id)["datasource_list"],
        HTTP_X_ORGANIZATION_ID=str(tenants.globex.id),
    )
    assert response.status_code == 200
    body = response.content.decode()
    assert "Acme DB" in body
    assert "Globex DB" not in body


def test_forged_header_cannot_grant_access_to_a_non_member_org(tenants, client_for, user):
    """The header is not an entitlement: naming an org the caller does not belong
    to changes nothing."""
    response = client_for(user).get(
        _urls(tenants.globex.id)["datasource_list"],
        HTTP_X_ORGANIZATION_ID=str(tenants.globex.id),
    )
    assert response.status_code == 404
    assert "Globex DB" not in response.content.decode()


def test_url_and_header_mismatch_is_rejected_safely(tenants, client_for, user):
    """URL says Globex, header says Acme: the URL scope is verified and refused."""
    response = client_for(user).get(
        _urls(tenants.globex.id)["datasource_list"],
        HTTP_X_ORGANIZATION_ID=str(tenants.acme.id),
    )
    assert response.status_code == 404
    assert "Globex DB" not in response.content.decode()
    assert "Acme DB" not in response.content.decode()


# --- C: no header means URL scope only (never a default/unauthorized org) -----

def test_without_header_scope_is_the_url_org_only(tenants, client_for, user):
    """A user who belongs to both orgs sees exactly the org in the URL."""
    Membership.objects.create(organization=tenants.globex, user=user, role=Role.VIEWER.value)
    client = client_for(user)

    acme_body = client.get(_urls(tenants.acme.id)["datasource_list"]).content.decode()
    globex_body = client.get(_urls(tenants.globex.id)["datasource_list"]).content.decode()

    assert "Acme DB" in acme_body and "Globex DB" not in acme_body
    assert "Globex DB" in globex_body and "Acme DB" not in globex_body


def test_without_header_a_non_member_still_fails_closed(tenants, client_for, user):
    response = client_for(user).get(_urls(tenants.globex.id)["datasource_list"])
    assert response.status_code == 404
    assert "Globex DB" not in response.content.decode()


# --- E: request body cannot override the scope --------------------------------

def test_body_organization_id_cannot_override_scope(tenants, client_for, user):
    payload = {**DATASOURCE_PAYLOAD, "organization_id": str(tenants.globex.id),
               "organization": str(tenants.globex.id)}
    with mock.patch("apps.datasources.services.validate_host"):
        response = client_for(user).post(
            _urls(tenants.acme.id)["datasource_list"], payload, format="json"
        )

    assert response.status_code == 201
    created = DataSource.objects.get(name=DATASOURCE_PAYLOAD["name"])
    assert created.organization_id == tenants.acme.id
    assert not DataSource.objects.filter(
        organization=tenants.globex, name=DATASOURCE_PAYLOAD["name"]
    ).exists()


def test_analyst_body_organization_cannot_override_scope(tenants, client_for, user):
    with mock.patch("apps.ai_bridge.services.AIServiceClient") as client_cls:
        client_cls.return_value.run_agent.return_value = {
            "answer": "ok", "steps": [], "provider": "p", "model": "m", "total_tokens": 1,
        }
        response = client_for(user).post(
            reverse("analyst-query", kwargs={"org_id": tenants.acme.id}),
            {"question": "Who owns this data?", "organization_id": str(tenants.globex.id)},
            format="json",
        )

    assert response.status_code == 201
    execution = Execution.objects.get(question="Who owns this data?")
    assert execution.organization_id == tenants.acme.id
    # The AI service is told the verified org, not the one in the body.
    sent = client_cls.return_value.run_agent.call_args.args[0]
    assert sent["organization_id"] == str(tenants.acme.id)


# --- F: query parameter cannot override the scope -----------------------------

def test_query_parameter_organization_id_cannot_override_scope(tenants, client_for, user):
    url = _urls(tenants.acme.id)["datasource_list"] + f"?organization_id={tenants.globex.id}"
    response = client_for(user).get(url)
    assert response.status_code == 200
    body = response.content.decode()
    assert "Acme DB" in body
    assert "Globex DB" not in body


# --- I: every tenant-scoped resource, positive and negative -------------------

def test_executions_are_scoped_to_the_verified_org(tenants, client_for, user):
    response = client_for(user).get(
        _urls(tenants.acme.id)["execution_list"],
        HTTP_X_ORGANIZATION_ID=str(tenants.globex.id),
    )
    assert response.status_code == 200
    assert "Globex secret question" not in response.content.decode()


def test_audit_logs_are_scoped_to_the_verified_org(tenants, client_for, user):
    response = client_for(user).get(
        _urls(tenants.acme.id)["audit_list"],
        HTTP_X_ORGANIZATION_ID=str(tenants.globex.id),
    )
    assert response.status_code == 200
    assert "globex.secret.event" not in response.content.decode()


def test_insights_aggregate_only_the_verified_org(tenants, client_for, user):
    response = client_for(user).get(
        _urls(tenants.acme.id)["insights"],
        HTTP_X_ORGANIZATION_ID=str(tenants.globex.id),
    )
    assert response.status_code == 200
    # Acme has exactly one execution; Globex's must not be counted.
    assert response.json()["executions"]["total"] == 1


def test_member_list_is_scoped_to_the_verified_org(tenants, client_for, user, other_user):
    response = client_for(user).get(
        _urls(tenants.acme.id)["member_list"],
        HTTP_X_ORGANIZATION_ID=str(tenants.globex.id),
    )
    assert response.status_code == 200
    body = response.content.decode()
    assert other_user.email not in body


def test_foreign_resources_return_404_without_disclosure(tenants, client_for, user):
    """Every cross-tenant object route answers 404 and leaks no data."""
    client = client_for(user)
    targets = {
        "organization": reverse("organization-detail", kwargs={"org_id": tenants.globex.id}),
        "datasource": reverse(
            "datasource-detail",
            kwargs={"org_id": tenants.globex.id, "datasource_id": tenants.globex_source.id},
        ),
        "document": reverse(
            "document-detail",
            kwargs={"org_id": tenants.globex.id, "document_id": tenants.globex_document.id},
        ),
        "execution": reverse(
            "execution-detail",
            kwargs={"org_id": tenants.globex.id, "execution_id": tenants.globex_execution.id},
        ),
        "audit": _urls(tenants.globex.id)["audit_list"],
        "insights": _urls(tenants.globex.id)["insights"],
    }
    for label, url in targets.items():
        response = client.get(url, HTTP_X_ORGANIZATION_ID=str(tenants.globex.id))
        assert response.status_code == 404, f"{label} -> {response.status_code}"
        assert "Globex" not in response.content.decode(), label


# --- G: internal (AI-service) endpoints cannot bypass authorization ----------

def test_internal_endpoint_requires_the_service_token(tenants, api_client):
    response = api_client.get(
        f"/internal/datasources/{tenants.acme_source.id}/connection",
        HTTP_X_DATAFORGE_ORG=str(tenants.acme.id),
    )
    # 401 or 403 depending on whether DRF advertises a challenge; both reject.
    assert response.status_code in {401, 403}


def test_internal_endpoint_cannot_cross_tenants(tenants, api_client):
    """A valid service token with the wrong org scope cannot reach another tenant."""
    response = api_client.get(
        f"/internal/datasources/{tenants.acme_source.id}/connection",
        HTTP_AUTHORIZATION=f"Bearer {SERVICE_TOKEN}",
        HTTP_X_DATAFORGE_ORG=str(tenants.globex.id),
    )
    assert response.status_code == 404


def test_internal_endpoint_scopes_to_the_declared_org(tenants, api_client):
    """Positive case: the correct org scope returns that org's own resource."""
    response = api_client.get(
        f"/internal/datasources/{tenants.acme_source.id}/connection",
        HTTP_AUTHORIZATION=f"Bearer {SERVICE_TOKEN}",
        HTTP_X_DATAFORGE_ORG=str(tenants.acme.id),
    )
    assert response.status_code == 200
    assert response.json()["connection"]["database"] == "acme"


def test_internal_document_search_is_scoped(tenants, api_client, user):
    """Vector search returns only the declared org's chunks."""
    from apps.documents.models import DocumentChunk

    acme_document = Document.objects.create(
        organization=tenants.acme, title="Acme handbook", original_filename="a.txt",
        content_type="text/plain", size_bytes=10, status=DocumentStatus.READY,
        uploaded_by=user,
    )

    def _chunk(document, content):
        vec = [0.0] * 1536
        vec[0] = 1.0
        return DocumentChunk.objects.create(
            document=document, organization=document.organization, chunk_index=0,
            content=content, char_count=len(content), embedding=vec,
        )

    _chunk(acme_document, "acme secret chunk")
    _chunk(tenants.globex_document, "globex secret chunk")
    embedding = [0.0] * 1536
    embedding[0] = 1.0

    response = api_client.post(
        "/internal/documents/search",
        {"embedding": embedding, "top_k": 5},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {SERVICE_TOKEN}",
        HTTP_X_DATAFORGE_ORG=str(tenants.globex.id),
    )

    assert response.status_code == 200
    assert [row["content"] for row in response.json()["results"]] == ["globex secret chunk"]


# --- The mechanism itself: the header must never resolve a tenant -------------
#
# These exercise the authorization code directly, without a view. They fail if a
# client-controlled header is ever allowed to decide the organization scope —
# which is exactly the regression this suite exists to prevent.

def _request(org_id_in_url=None, header_org_id=None, user=None):
    factory = APIRequestFactory()
    headers = {"HTTP_X_ORGANIZATION_ID": str(header_org_id)} if header_org_id else {}
    request = factory.get("/api/v1/me/", **headers)
    request.resolver_match = SimpleNamespace(kwargs=({"org_id": str(org_id_in_url)} if org_id_in_url else {}))
    request.user = user
    return request


def test_client_header_alone_never_resolves_an_organization(organization, user):
    request = _request(header_org_id=organization.id, user=user)
    assert OrganizationAccess.resolve_org_id(request) is None


def test_client_header_alone_never_produces_a_membership(organization, user):
    request = _request(header_org_id=organization.id, user=user)
    assert OrganizationAccess().get_membership(request) is None


def test_require_organization_fails_closed_without_url_scope(organization, user):
    request = _request(header_org_id=organization.id, user=user)
    with pytest.raises(NotFound):
        require_organization(request)


def test_url_scope_is_verified_and_wins_over_a_forged_header(organization, user, other_user):
    """URL = Acme (member), header = Globex (also a member): Acme is used."""
    globex = Organization.objects.create(name="Globex", slug="globex-wins", created_by=other_user)
    Membership.objects.create(organization=globex, user=user, role=Role.VIEWER.value)

    request = _request(org_id_in_url=organization.id, header_org_id=globex.id, user=user)

    assert require_organization(request).id == organization.id


def test_url_scope_without_membership_is_refused_despite_a_valid_header(organization, user, other_user):
    """URL = Globex (not a member), header = Acme (member): refused, not granted."""
    globex = Organization.objects.create(name="Globex", slug="globex-refused", created_by=other_user)

    request = _request(org_id_in_url=globex.id, header_org_id=organization.id, user=user)

    with pytest.raises(NotFound):
        require_organization(request)
