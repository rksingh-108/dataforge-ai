"""Orchestration between the API and the AI service for analyst queries.

The API owns the execution record and the audit trail; the AI service owns the
agent reasoning. This module is the single place where those meet.
"""
from __future__ import annotations

import logging

from django.db import transaction

from apps.ai_bridge.client import AIServiceClient
from apps.analytics.models import ExecutionKind, ExecutionStatus
from apps.analytics.services import add_step, finish_execution, start_execution
from apps.common.exceptions import UpstreamServiceError
from apps.datasources import selectors as datasource_selectors

logger = logging.getLogger("apps.ai_bridge")


def _authorized_datasource_ids(organization_id, requested_ids) -> list[str]:
    """Filter the requested ids to those the organization actually owns.

    Unknown or foreign ids are ignored rather than trusted — this is the tenant
    check for the AI layer.
    """
    if not requested_ids:
        return []
    owned = {
        str(ds.id)
        for ds in datasource_selectors.list_datasources(organization_id=organization_id)
    }
    return [str(x) for x in requested_ids if str(x) in owned]


def run_analyst_query(
    *,
    organization,
    user,
    question: str,
    datasource_ids: list | None = None,
    use_documents: bool = True,
    request_id: str | None = None,
    client: AIServiceClient | None = None,
):
    """Run the analyst agent and return the resulting `Execution`."""
    client = client or AIServiceClient()
    allowed_datasource_ids = _authorized_datasource_ids(organization.id, datasource_ids or [])

    execution = start_execution(
        organization=organization,
        user=user,
        kind=ExecutionKind.ANALYST_QUERY,
        question=question,
    )

    payload = {
        "question": question,
        "organization_id": str(organization.id),
        "datasource_ids": allowed_datasource_ids,
        "use_documents": bool(use_documents),
        "execution_id": str(execution.id),
    }

    try:
        result = client.run_agent(
            payload,
            organization_id=organization.id,
            user_id=getattr(user, "id", None),
            request_id=request_id,
        )
    except UpstreamServiceError:
        finish_execution(execution=execution, status=ExecutionStatus.FAILED,
                         error="The AI service could not complete the request.")
        raise
    except Exception as exc:
        finish_execution(execution=execution, status=ExecutionStatus.FAILED, error=str(exc))
        logger.warning("Analyst query failed for execution %s: %s", execution.id, exc)
        raise UpstreamServiceError(str(exc)) from exc

    with transaction.atomic():
        for step in result.get("steps", []):
            add_step(
                execution=execution,
                index=int(step.get("index", 0)),
                tool_name=str(step.get("tool", "")),
                title=str(step.get("title", ""))[:200],
                status=str(step.get("status", ExecutionStatus.SUCCEEDED)),
                input_summary=step.get("input_summary", {}) or {},
                output_summary=step.get("output_summary", {}) or {},
                duration_ms=int(step.get("duration_ms", 0) or 0),
                error=str(step.get("error", ""))[:2000],
            )
        finish_execution(
            execution=execution,
            status=ExecutionStatus.SUCCEEDED,
            answer=str(result.get("answer", "")),
            provider=str(result.get("provider", ""))[:64],
            model_name=str(result.get("model", ""))[:128],
            total_tokens=int(result.get("total_tokens", 0) or 0),
        )

    execution.refresh_from_db()
    return execution
