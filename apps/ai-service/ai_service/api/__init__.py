"""HTTP API for the AI service (internal only)."""
from __future__ import annotations

import logging
import uuid

from flask import Blueprint, g, jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger("ai_service.api")


def error_response(code: str, message: str, status: int = 400, details: dict | None = None):
    return (
        jsonify({"error": {"code": code, "message": message, "details": details or {},
                           "request_id": getattr(g, "request_id", None)}}),
        status,
    )


def register_error_handlers(app) -> None:
    @app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException):
        return error_response(exc.name.lower().replace(" ", "_"),
                              exc.description or exc.name, exc.code or 500)

    @app.errorhandler(Exception)
    def _unexpected(exc: Exception):
        logger.exception("Unhandled error in AI service")
        return error_response("internal_error", "An unexpected error occurred.", 500)


def build_blueprint() -> Blueprint:
    """Assemble the versioned API blueprint."""
    from ai_service.api.agent_routes import bp as agent_bp
    from ai_service.api.datasource_routes import bp as datasource_bp
    from ai_service.api.health import bp as health_bp
    from ai_service.api.rag_routes import bp as rag_bp

    root = Blueprint("api", __name__)
    root.register_blueprint(health_bp)
    root.register_blueprint(datasource_bp)
    root.register_blueprint(rag_bp)
    root.register_blueprint(agent_bp)
    return root


def new_request_id() -> str:
    return str(uuid.uuid4())


__all__ = ["build_blueprint", "error_response", "register_error_handlers"]
