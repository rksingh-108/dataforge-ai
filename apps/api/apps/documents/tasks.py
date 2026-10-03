"""Celery tasks for document processing.

The task calls the AI service to extract text, chunk it and produce embeddings,
then persists the chunks (with vectors) into the platform database. Persisting is
done here because the API is the only writer to the platform database.
"""
from __future__ import annotations

import base64
import logging

from celery import shared_task
from django.utils import timezone

from apps.ai_bridge.client import AIServiceClient
from apps.analytics.services import record_audit
from apps.documents.models import Document, DocumentChunk, DocumentStatus

logger = logging.getLogger("apps.documents.tasks")

# Bound the payload we hand to the AI service in one call. Larger files should be
# chunked at the storage layer; documented as a known limitation.
_MAX_INLINE_BYTES = 25 * 1024 * 1024


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def process_document(self, document_id: str) -> dict:
    document = Document.objects.filter(id=document_id).select_related("organization").first()
    if document is None:
        logger.warning("process_document called for unknown document %s", document_id)
        return {"status": "skipped", "reason": "not_found"}

    if document.size_bytes > _MAX_INLINE_BYTES:
        return _fail(document, "Document exceeds the inline processing limit.")

    try:
        payload = _build_payload(document)
        result = AIServiceClient().process_document(payload)
        _persist_chunks(document, result)
    except Exception as exc:
        logger.exception("Document processing failed for %s", document_id)
        # Record the failure immediately so operators see it even if a retry
        # later succeeds; a successful retry overwrites the status to READY.
        failure = _fail(document, str(exc))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        return failure

    document.status = DocumentStatus.READY
    document.error = ""
    document.processed_at = timezone.now()
    document.page_count = int(result.get("page_count", 0) or 0)
    document.chunk_count = int(result.get("chunk_count", 0) or 0)
    document.save(
        update_fields=[
            "status", "error", "processed_at", "page_count", "chunk_count", "updated_at"
        ]
    )
    record_audit(
        organization=document.organization,
        actor=None,
        action="document.processed",
        target_type="document",
        target_id=str(document.id),
        metadata={"chunks": document.chunk_count, "pages": document.page_count},
    )
    return {"status": "ready", "chunks": document.chunk_count}


def _build_payload(document: Document) -> dict:
    with document.file.open("rb") as handle:
        raw = handle.read()
    return {
        "document_id": str(document.id),
        "organization_id": str(document.organization_id),
        "filename": document.original_filename,
        "content_type": document.content_type,
        "content_base64": base64.b64encode(raw).decode("ascii"),
    }


def _persist_chunks(document: Document, result: dict) -> None:
    chunks = result.get("chunks", [])
    if not chunks:
        raise ValueError("The AI service returned no chunks for the document.")

    DocumentChunk.objects.filter(document=document).delete()
    rows = []
    for chunk in chunks:
        row = DocumentChunk(
            document=document,
            organization=document.organization,
            chunk_index=int(chunk["index"]),
            content=chunk["content"],
            char_count=len(chunk["content"]),
            source_label=str(chunk.get("source_label", ""))[:200],
            metadata=chunk.get("metadata", {}),
        )
        row.set_embedding([float(v) for v in chunk["embedding"]])
        rows.append(row)
    DocumentChunk.objects.bulk_create(rows, batch_size=100)


def _fail(document: Document, message: str) -> dict:
    document.status = DocumentStatus.FAILED
    document.error = message[:2000]
    document.save(update_fields=["status", "error", "updated_at"])
    record_audit(
        organization=document.organization,
        actor=None,
        action="document.processing_failed",
        target_type="document",
        target_id=str(document.id),
        metadata={"reason": message[:200]},
    )
    return {"status": "failed", "error": message}
