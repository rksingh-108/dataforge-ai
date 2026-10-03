"""Document retrieval tool backed by pgvector search in the platform API."""
from __future__ import annotations

import logging

from ai_service.security.injection import scan_for_injection, summarise_findings
from ai_service.tools.registry import ToolContext, ToolError

logger = logging.getLogger("ai_service.tools.documents")


def search_documents(context: ToolContext, query: str, top_k: int | None = None) -> dict:
    if not query or not query.strip():
        raise ToolError("query is required.")
    settings = context.settings
    limit = int(top_k or settings.rag_top_k)
    limit = max(1, min(limit, 20))

    try:
        vectors = context.embedder.embed([query])
    except Exception as exc:
        raise ToolError(f"Could not embed the query: {str(exc)[:200]}") from exc

    try:
        results = context.api_client.search_documents(
            vectors[0], top_k=limit, document_ids=context.document_ids or None
        )
    except Exception as exc:
        raise ToolError(f"Document search failed: {str(exc)[:200]}") from exc

    findings = []
    for result in results:
        findings.extend(scan_for_injection(result.get("content", "")))

    return {
        "query": query,
        "match_count": len(results),
        "content_scan": summarise_findings(findings),
        "passages": [
            {
                "document_id": r["document_id"],
                "document_title": r["document_title"],
                "source_label": r.get("source_label", ""),
                "similarity": r.get("similarity"),
                "content": r["content"],
            }
            for r in results
        ],
    }
