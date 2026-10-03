"""HTTP layer tests: auth enforcement, request validation and happy paths."""
from __future__ import annotations

import base64

from ai_service.providers.base import LLMResponse
from tests.conftest import INTERNAL_TOKEN, ORG_ID


def test_health_is_public(client):
    response = client.get("/_health/")
    assert response.status_code == 200
    body = response.get_json()
    assert body["service"] == "dataforge-ai-service"
    assert body["checks"]["llm_provider"] == "openai_compatible"


def test_agent_requires_service_token(client):
    response = client.post("/v1/agent/run", json={"question": "hi"})
    assert response.status_code == 401


def test_agent_rejects_wrong_token(client):
    response = client.post("/v1/agent/run", json={"question": "hi"},
                           headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_agent_requires_org_scope(client):
    response = client.post("/v1/agent/run", json={"question": "hi"},
                           headers={"Authorization": f"Bearer {INTERNAL_TOKEN}"})
    assert response.status_code == 400


def test_agent_rejects_invalid_org_scope(client):
    response = client.post(
        "/v1/agent/run", json={"question": "hi"},
        headers={"Authorization": f"Bearer {INTERNAL_TOKEN}", "X-DataForge-Org": "not-a-uuid"},
    )
    assert response.status_code == 400


def test_agent_run_returns_answer(app, client):
    app.extensions["llm_provider"]._responses = [LLMResponse(content="All good.", model="test-model")]
    response = client.post(
        "/v1/agent/run",
        json={"question": "How are we doing?", "datasource_ids": []},
        headers={"Authorization": f"Bearer {INTERNAL_TOKEN}", "X-DataForge-Org": ORG_ID},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["answer"] == "All good."
    assert body["provider"] == "scripted"


def test_agent_run_requires_question(client, auth_headers):
    response = client.post("/v1/agent/run", json={}, headers=auth_headers)
    assert response.status_code == 400


def test_rag_process_extracts_and_embeds(client, auth_headers, settings):
    content = base64.b64encode(b"Refunds are allowed within 30 days. " * 30).decode()
    response = client.post(
        "/v1/rag/process",
        json={"filename": "policy.txt", "content_type": "text/plain",
              "content_base64": content},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["chunk_count"] >= 1
    assert len(body["chunks"][0]["embedding"]) == settings.embeddings.dim


def test_rag_process_rejects_bad_base64(client, auth_headers):
    response = client.post(
        "/v1/rag/process",
        json={"filename": "policy.txt", "content_type": "text/plain",
              "content_base64": "!!!not-base64!!!"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_rag_process_rejects_unsupported_type(client, auth_headers):
    content = base64.b64encode(b"MZ\x90\x00").decode()
    response = client.post(
        "/v1/rag/process",
        json={"filename": "evil.exe", "content_type": "application/octet-stream",
              "content_base64": content},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_embeddings_query_returns_vector(client, auth_headers, settings):
    response = client.post("/v1/embeddings/query", json={"text": "hello"},
                           headers=auth_headers)
    assert response.status_code == 200
    assert len(response.get_json()["embedding"]) == settings.embeddings.dim


def test_datasource_test_rejects_private_host(client, auth_headers):
    response = client.post(
        "/v1/datasources/test",
        json={"connection": {"engine": "postgresql", "host": "127.0.0.1", "port": 5432,
                             "database": "x", "username": "u", "password": "p"}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.get_json()["ok"] is False
    assert "not allowed" in response.get_json()["error"]


def test_datasource_test_rejects_unsupported_engine(client, auth_headers):
    response = client.post(
        "/v1/datasources/test",
        json={"connection": {"engine": "oracle", "host": "db.example.com", "port": 1521,
                             "database": "x", "username": "u", "password": "p"}},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_correlation_id_is_echoed(client, auth_headers):
    response = client.post("/v1/embeddings/query", json={"text": "hello"}, headers=auth_headers)
    assert "X-Request-Id" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
