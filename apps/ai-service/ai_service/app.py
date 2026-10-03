"""Flask application factory.

Provider instances are built once and stored on `app.extensions`, so routes never
construct providers themselves. That keeps provider selection a pure configuration
concern.
"""
from __future__ import annotations

import logging
import uuid

from flask import Flask, g, request

from ai_service.api import build_blueprint, register_error_handlers
from ai_service.config import Settings, get_settings
from ai_service.providers.registry import build_embedding_provider, build_llm_provider
from ai_service.tools.registry import build_default_registry


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or get_settings()
    app = Flask(__name__)
    app.config.update(_flask_config(settings))

    _configure_logging(settings)
    register_error_handlers(app)

    # Build providers once at startup. A bad provider name fails fast here.
    app.extensions["settings"] = settings
    app.extensions["llm_provider"] = build_llm_provider(settings.llm)
    app.extensions["embedding_provider"] = build_embedding_provider(settings.embeddings)
    app.extensions["tool_registry"] = build_default_registry()

    @app.before_request
    def _correlation_id():
        incoming = request.headers.get("X-Request-Id", "")
        try:
            g.request_id = str(uuid.UUID(incoming))
        except (ValueError, TypeError):
            g.request_id = str(uuid.uuid4())

    @app.after_request
    def _echo_correlation_id(response):
        response.headers["X-Request-Id"] = getattr(g, "request_id", "-")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    app.register_blueprint(build_blueprint())
    return app


def _flask_config(settings: Settings) -> dict:
    return {
        "INTERNAL_SERVICE_TOKEN": settings.internal_service_token,
        "API_BASE_URL": settings.api_base_url,
        "API_REQUEST_TIMEOUT_SECONDS": 60,
        "LLM_PROVIDER": settings.llm.provider,
        "LLM_MODEL": settings.llm.model,
        "EMBEDDING_PROVIDER": settings.embeddings.provider,
        "EMBEDDING_DIM": settings.embeddings.dim,
        "RAG_CHUNK_SIZE": settings.rag_chunk_size,
        "RAG_CHUNK_OVERLAP": settings.rag_chunk_overlap,
        "RAG_TOP_K": settings.rag_top_k,
        "SQL_STATEMENT_TIMEOUT_MS": settings.sql_statement_timeout_ms,
        "SQL_MAX_ROWS": settings.sql_max_rows,
        "SQL_MAX_JOINS": settings.sql_max_joins,
        "SQL_CONNECT_TIMEOUT_SECONDS": settings.sql_connect_timeout_seconds,
        "AGENT_MAX_ITERATIONS": settings.agent_max_iterations,
        "ALLOW_PRIVATE_NETWORKS": settings.allow_private_networks,
        "MAX_CONTENT_LENGTH": 40 * 1024 * 1024,
    }


def _configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Never log the token, even at DEBUG.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
