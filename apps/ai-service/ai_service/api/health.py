"""Health endpoint (the only unauthenticated route)."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify

bp = Blueprint("health", __name__)


@bp.get("/_health/")
def health():
    """Liveness + configuration readiness.

    Reports which provider is configured (a name, never a key) so an operator can
    confirm deployment config without opening a shell.
    """
    checks = {
        "internal_token_configured": bool(current_app.config.get("INTERNAL_SERVICE_TOKEN")),
        "api_base_url_configured": bool(current_app.config.get("API_BASE_URL")),
        "llm_provider": current_app.config.get("LLM_PROVIDER", ""),
        "llm_model": current_app.config.get("LLM_MODEL", ""),
        "embedding_provider": current_app.config.get("EMBEDDING_PROVIDER", ""),
        "embedding_dim": current_app.config.get("EMBEDDING_DIM"),
    }
    ready = checks["internal_token_configured"] and checks["api_base_url_configured"]
    return jsonify(
        {"status": "ok" if ready else "degraded", "service": "dataforge-ai-service",
         "checks": checks}
    ), (200 if ready else 503)
