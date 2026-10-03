"""Shared fixtures for the AI service test suite.

The app is built with an explicit test Settings object so tests never depend on a
populated environment. Provider instances are replaced with deterministic test
doubles (see `providers/testing.py`).
"""
from __future__ import annotations

import pytest

from ai_service.config import EmbeddingSettings, LLMSettings, Settings

INTERNAL_TOKEN = "test-internal-service-token"
ORG_ID = "11111111-1111-1111-1111-111111111111"
OTHER_ORG_ID = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        internal_service_token=INTERNAL_TOKEN,
        api_base_url="http://api.invalid",
        llm=LLMSettings(
            provider="openai_compatible",
            model="test-model",
            api_key="test-key",
            base_url="http://llm.invalid/v1",
            timeout_seconds=5,
            max_tokens=512,
            temperature=0.0,
        ),
        embeddings=EmbeddingSettings(
            provider="openai_compatible",
            model="test-embed",
            dim=64,
            api_key="test-key",
            base_url="http://llm.invalid/v1",
        ),
        rag_chunk_size=200,
        rag_chunk_overlap=20,
        rag_top_k=5,
        sql_statement_timeout_ms=2000,
        sql_max_rows=100,
        sql_max_joins=4,
        sql_connect_timeout_seconds=2,
        agent_max_iterations=4,
        allow_private_networks=False,
    )


@pytest.fixture
def app(settings):
    from ai_service.app import create_app
    from ai_service.providers.testing import DeterministicEmbeddingProvider, ScriptedProvider

    application = create_app(settings)
    application.extensions["llm_provider"] = ScriptedProvider()
    application.extensions["embedding_provider"] = DeterministicEmbeddingProvider(settings.embeddings)
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {INTERNAL_TOKEN}", "X-DataForge-Org": ORG_ID}
