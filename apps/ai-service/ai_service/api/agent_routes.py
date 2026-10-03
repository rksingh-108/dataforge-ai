"""The agent run endpoint.

This is the AI service's main entry point. It requires the service token AND an
organization scope: the AI service will never run a query without knowing which
tenant it is acting for.
"""
from __future__ import annotations

import logging

from flask import Blueprint, current_app, g, jsonify, request

from ai_service.agents.orchestrator import AgentRunError, run_agent
from ai_service.api import error_response
from ai_service.clients.api_client import PlatformAPIClient
from ai_service.security.internal_auth import require_internal_token, require_organization_scope
from ai_service.tools.registry import ToolContext

bp = Blueprint("agent", __name__, url_prefix="/v1/agent")
logger = logging.getLogger("ai_service.api.agent")


@bp.post("/run")
@require_internal_token
@require_organization_scope
def agent_run():
    payload = request.get_json(silent=True) or {}
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        return error_response("bad_request", "`question` is required.")

    datasource_ids = [str(x) for x in payload.get("datasource_ids", []) if x]
    datasource_names = {str(k): str(v) for k, v in (payload.get("datasource_names") or {}).items()}
    document_ids = [str(x) for x in payload.get("document_ids", []) if x]
    use_documents = bool(payload.get("use_documents", True))

    registry = current_app.extensions["tool_registry"]
    if not use_documents:
        registry = _without_documents(registry)

    context = ToolContext(
        organization_id=g.organization_id,
        datasource_ids=datasource_ids,
        datasource_names=datasource_names,
        document_ids=document_ids,
        embedder=current_app.extensions["embedding_provider"],
        api_client=PlatformAPIClient(),
        settings=current_app.extensions["settings"],
    )

    try:
        result = run_agent(
            question=question,
            provider=current_app.extensions["llm_provider"],
            registry=registry,
            context=context,
            max_iterations=current_app.config["AGENT_MAX_ITERATIONS"],
        )
    except AgentRunError as exc:
        status = 502 if exc.code == "provider_error" else 400
        return error_response(exc.code, str(exc), status)
    except Exception:
        logger.exception("Agent run failed unexpectedly")
        return error_response("agent_error", "The analysis could not be completed.", 500)

    return jsonify(result)


def _without_documents(registry):
    """Return a registry view that omits document tools for this run."""
    from ai_service.tools.registry import ToolRegistry

    filtered = ToolRegistry()
    for tool in registry._tools.values():
        if tool.name != "search_documents":
            filtered.register(tool)
    return filtered
