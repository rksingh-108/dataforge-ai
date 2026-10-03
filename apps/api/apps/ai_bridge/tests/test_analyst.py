"""Analyst query tests: orchestration, execution recording, permissions."""
from __future__ import annotations

from unittest import mock

import pytest
from django.urls import reverse

from apps.analytics.models import Execution, ExecutionStatus
from apps.common.rbac import Role

pytestmark = pytest.mark.django_db


def _query(org_id):
    return reverse("analyst-query", kwargs={"org_id": org_id})


AGENT_RESULT = {
    "answer": "Revenue in Q3 was 120000.",
    "provider": "openai_compatible",
    "model": "gpt-4o-mini",
    "total_tokens": 812,
    "steps": [
        {"index": 0, "tool": "document_search", "title": "Search documents", "status": "succeeded",
         "input_summary": {"query": "Q3 revenue"}, "output_summary": {"matches": 2},
         "duration_ms": 210},
        {"index": 1, "tool": "sql_query", "title": "Query orders table", "status": "succeeded",
         "input_summary": {"datasource_id": "x"}, "output_summary": {"rows": 4},
         "duration_ms": 340},
    ],
}


def test_analyst_query_records_execution_and_steps(auth_client, organization):
    with mock.patch("apps.ai_bridge.services.AIServiceClient") as client_cls:
        client_cls.return_value.run_agent.return_value = AGENT_RESULT
        response = auth_client.post(_query(organization.id), {"question": "Q3 revenue?"},
                                    format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == ExecutionStatus.SUCCEEDED
    assert body["answer"] == AGENT_RESULT["answer"]
    assert [s["tool_name"] for s in body["steps"]] == ["document_search", "sql_query"]
    assert body["total_tokens"] == 812


def test_analyst_query_failure_is_recorded(auth_client, organization):
    with mock.patch("apps.ai_bridge.services.AIServiceClient") as client_cls:
        client_cls.return_value.run_agent.side_effect = Exception("ai service down")
        response = auth_client.post(_query(organization.id), {"question": "anything"},
                                    format="json")

    assert response.status_code == 502
    execution = Execution.objects.get(organization=organization)
    assert execution.status == ExecutionStatus.FAILED
    assert "ai service down" in execution.error


def test_analyst_query_rejects_short_question(auth_client, organization):
    response = auth_client.post(_query(organization.id), {"question": "hi"}, format="json")
    assert response.status_code == 400


def test_viewer_cannot_run_analyst(organization, make_member):
    _viewer, client = make_member(organization, Role.VIEWER.value)
    response = client.post(_query(organization.id), {"question": "What happened?"}, format="json")
    assert response.status_code == 403


def test_datasource_ids_are_filtered_to_owned_ones(auth_client, organization, user):
    from apps.datasources.models import DataSource

    owned = DataSource.objects.create(
        organization=organization, name="Owned", engine="postgresql", host="db.example.com",
        port=5432, database_name="x", username="u", password_encrypted=b"x", created_by=user,
    )
    foreign_id = "11111111-1111-1111-1111-111111111111"

    with mock.patch("apps.ai_bridge.services.AIServiceClient") as client_cls:
        client_cls.return_value.run_agent.return_value = AGENT_RESULT
        auth_client.post(
            _query(organization.id),
            {"question": "Use my data", "datasource_ids": [str(owned.id), foreign_id]},
            format="json",
        )

    sent = client_cls.return_value.run_agent.call_args.args[0]
    assert sent["datasource_ids"] == [str(owned.id)]
