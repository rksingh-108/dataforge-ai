"""Data source tests: creation, credentials, connection testing, isolation, SSRF."""
from __future__ import annotations

from unittest import mock

import pytest
from django.urls import reverse

from apps.common.rbac import Role
from apps.datasources.models import DataSource, DataSourceStatus, SchemaTable
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db

PUBLIC_HOST = "db.example.com"


def _list(org_id):
    return reverse("datasource-list", kwargs={"org_id": org_id})


def _detail(org_id, ds_id):
    return reverse("datasource-detail", kwargs={"org_id": org_id, "datasource_id": ds_id})


def _payload(**overrides):
    data = {
        "name": "Warehouse",
        "engine": "postgresql",
        "host": PUBLIC_HOST,
        "port": 5432,
        "database_name": "analytics",
        "username": "readonly",
        "password": "sup3r-secret",
    }
    data.update(overrides)
    return data


@pytest.fixture(autouse=True)
def _public_dns():
    """Make the test host resolve to a public IP so the SSRF validator permits it.

    The validator itself is *not* patched - these tests exercise the real thing.
    """
    with mock.patch(
        "apps.datasources.validators._default_resolver", return_value=["93.184.216.34"]
    ):
        yield


def test_create_datasource_encrypts_password(auth_client, organization):
    response = auth_client.post(_list(organization.id), _payload(), format="json")
    assert response.status_code == 201
    datasource = DataSource.objects.get(id=response.json()["id"])
    assert datasource.get_password() == "sup3r-secret"
    assert b"sup3r-secret" not in bytes(datasource.password_encrypted)


def test_password_never_serialized(auth_client, organization):
    response = auth_client.post(_list(organization.id), _payload(), format="json")
    assert "password" not in response.json()
    assert "sup3r-secret" not in response.content.decode()
    assert "sup3r-secret" not in auth_client.get(_list(organization.id)).content.decode()


def test_datasource_is_tenant_isolated(auth_client, organization, other_user, client_for):
    created = auth_client.post(_list(organization.id), _payload(), format="json").json()

    foreign_org = Organization.objects.create(name="Globex", slug="globex", created_by=other_user)
    Membership.objects.create(organization=foreign_org, user=other_user, role=Role.OWNER.value)
    rival = client_for(other_user)

    assert rival.get(_list(foreign_org.id)).json()["results"] == []
    assert rival.get(_detail(foreign_org.id, created["id"])).status_code == 404


def test_viewer_cannot_create_datasource(organization, make_member):
    _viewer, client = make_member(organization, Role.VIEWER.value)
    assert client.post(_list(organization.id), _payload(), format="json").status_code == 403


def test_ssrf_validation_rejects_cloud_metadata(auth_client, organization):
    response = auth_client.post(
        _list(organization.id), _payload(host="169.254.169.254"), format="json"
    )
    assert response.status_code == 400


def test_ssrf_validation_rejects_loopback(auth_client, organization):
    response = auth_client.post(_list(organization.id), _payload(host="127.0.0.1"), format="json")
    assert response.status_code == 400


def test_ssrf_validation_rejects_private_network(auth_client, organization):
    response = auth_client.post(_list(organization.id), _payload(host="10.0.0.5"), format="json")
    assert response.status_code == 400


def test_connection_test_marks_status(auth_client, organization):
    created = auth_client.post(_list(organization.id), _payload(), format="json").json()
    url = reverse("datasource-test",
                  kwargs={"org_id": organization.id, "datasource_id": created["id"]})
    with mock.patch("apps.datasources.services.AIServiceClient") as client_cls:
        client_cls.return_value.test_connection.return_value = {"ok": True, "server_version": "16.3"}
        response = auth_client.post(url)
    assert response.status_code == 200
    datasource = DataSource.objects.get(id=created["id"])
    assert datasource.status == DataSourceStatus.CONNECTED
    assert datasource.last_tested_at is not None


def test_connection_failure_records_error(auth_client, organization):
    created = auth_client.post(_list(organization.id), _payload(), format="json").json()
    url = reverse("datasource-test",
                  kwargs={"org_id": organization.id, "datasource_id": created["id"]})
    with mock.patch("apps.datasources.services.AIServiceClient") as client_cls:
        client_cls.return_value.test_connection.side_effect = Exception("connection refused")
        response = auth_client.post(url)
    assert response.status_code == 422
    datasource = DataSource.objects.get(id=created["id"])
    assert datasource.status == DataSourceStatus.ERROR
    assert "connection refused" in datasource.last_error


def test_schema_sync_persists_tables_and_columns(auth_client, organization):
    created = auth_client.post(_list(organization.id), _payload(), format="json").json()
    url = reverse("datasource-schema-sync",
                  kwargs={"org_id": organization.id, "datasource_id": created["id"]})
    introspection = {
        "tables": [
            {
                "schema": "public",
                "name": "orders",
                "row_estimate": 1200,
                "columns": [
                    {"name": "id", "data_type": "integer", "nullable": False,
                     "primary_key": True, "position": 1},
                    {"name": "total", "data_type": "numeric", "nullable": True,
                     "primary_key": False, "position": 2},
                ],
            }
        ]
    }
    with mock.patch("apps.datasources.services.AIServiceClient") as client_cls:
        client_cls.return_value.introspect.return_value = introspection
        response = auth_client.post(url)
    assert response.status_code == 200
    assert response.json() == {"tables": 1, "columns": 2}
    assert SchemaTable.objects.filter(datasource_id=created["id"]).count() == 1
