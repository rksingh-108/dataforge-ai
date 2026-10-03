"""Services for documents.

Uploads are validated and stored synchronously; the expensive RAG work
(extraction, chunking, embedding) happens asynchronously in a Celery task so an
HTTP request never blocks on an LLM/embedding provider.
"""
from __future__ import annotations

import logging

from django.db import transaction

from apps.analytics.services import record_audit
from apps.common.exceptions import Conflict
from apps.documents.models import Document, DocumentStatus
from apps.documents.validators import validate_upload

logger = logging.getLogger("apps.documents")


@transaction.atomic
def create_document(*, organization, actor, uploaded_file, title: str = "") -> Document:
    metadata = validate_upload(uploaded_file)

    # Duplicate content in the same organization is a conflict, not corruption:
    # the DB also enforces this with a partial unique constraint.
    if Document.objects.filter(
        organization=organization, checksum_sha256=metadata["checksum_sha256"]
    ).exists():
        raise Conflict("This exact document has already been uploaded to the organization.")

    document = Document(
        organization=organization,
        title=(title or uploaded_file.name).strip()[:255],
        original_filename=uploaded_file.name[:255],
        content_type=metadata["content_type"],
        size_bytes=metadata["size_bytes"],
        checksum_sha256=metadata["checksum_sha256"],
        status=DocumentStatus.PENDING,
        uploaded_by=actor,
    )
    document.file.save(uploaded_file.name, uploaded_file, save=False)
    document.save()

    record_audit(
        organization=organization,
        actor=actor,
        action="document.uploaded",
        target_type="document",
        target_id=str(document.id),
        metadata={"filename": document.original_filename, "size_bytes": document.size_bytes},
    )
    return document


@transaction.atomic
def delete_document(*, document: Document, actor) -> None:
    organization = document.organization
    document_id = str(document.id)
    title = document.title
    document.file.delete(save=False)
    document.delete()
    record_audit(
        organization=organization,
        actor=actor,
        action="document.deleted",
        target_type="document",
        target_id=document_id,
        metadata={"title": title},
    )


def enqueue_processing(*, document: Document) -> None:
    """Schedule asynchronous RAG processing. Idempotent per document."""
    from apps.documents.tasks import process_document

    document.status = DocumentStatus.PROCESSING
    document.error = ""
    document.save(update_fields=["status", "error", "updated_at"])
    process_document.delay(str(document.id))
