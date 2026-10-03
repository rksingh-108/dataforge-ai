"""Execution history, insights and audit-log tests."""
from __future__ import annotations

import pytest
from django.urls import reverse

from apps.analytics.models import AuditLog, Execution, ExecutionKind, ExecutionStatus
from apps.common.rbac import Role

pytestmark = pytest.mark.django_db


def _executions(org_id):
    return reverse("execution-list", kwargs={"org_id": org_id})


def _insights(org_id):
    return reverse("insights", kwargs={"org_id": org_id})


def _audit(org_id):
    return reverse("audit-log-list", kwargs={"org_id": org_id})


def _make_execution(organization, user, status=ExecutionStatus.SUCCEEDED, question="q"):
    return Execution.objects.create(
        organization=organization,
        user=user,
        kind=ExecutionKind.ANALYST_QUERY,
        status=status,
        question=question,
    )


def test_insights_reports_real_aggregates(auth_client, organization, user):
    _make_execution(organization, user, ExecutionStatus.SUCCEEDED)
    _make_execution(organization, user, ExecutionStatus.SUCCEEDED)
    _make_execution(organization, user, ExecutionStatus.FAILED)

    body = auth_client.get(_insights(organization.id)).json()

    assert body["executions"]["total"] == 3
    assert body["executions"]["succeeded"] == 2
    assert body["executions"]["failed"] == 1
    assert body["executions"]["success_rate_percent"] == pytest.approx(66.7, abs=0.1)


def test_execution_list_is_tenant_scoped(auth_client, organization, user, other_user, client_for):
    from apps.organizations.models import Membership, Organization

    _make_execution(organization, user, question="mine")
    foreign = Organization.objects.create(name="Globex", slug="globex", created_by=other_user)
    Membership.objects.create(organization=foreign, user=other_user, role=Role.OWNER.value)
    _make_execution(foreign, other_user, question="theirs")

    body = auth_client.get(_executions(organization.id)).json()
    assert [row["question"] for row in body["results"]] == ["mine"]


def test_analyst_cannot_read_audit_logs(organization, make_member):
    _analyst, client = make_member(organization, Role.ANALYST.value)
    assert client.get(_audit(organization.id)).status_code == 403


def test_admin_can_read_audit_logs(organization, make_member):
    _admin, client = make_member(organization, Role.ADMIN.value)
    AuditLog.objects.create(organization=organization, action="datasource.created")
    response = client.get(_audit(organization.id))
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_audit_log_is_append_only(organization):
    entry = AuditLog.objects.create(organization=organization, action="auth.login")
    entry.action = "tampered"
    with pytest.raises(ValueError):
        entry.save()
    with pytest.raises(ValueError):
        entry.delete()
