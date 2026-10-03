"""Selectors for documents and the pgvector similarity search used by RAG."""
from __future__ import annotations

import uuid

from django.db.models import QuerySet


def list_documents(*, organization_id: uuid.UUID, status: str | None = None) -> QuerySet:
    from apps.documents.models import Document

    qs = Document.objects.filter(organization_id=organization_id)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def get_document(*, organization_id: uuid.UUID, document_id: uuid.UUID):
    from apps.documents.models import Document

    return Document.objects.filter(id=document_id, organization_id=organization_id).first()


def search_chunks(*, organization_id: uuid.UUID, embedding: list[float], top_k: int = 5,
                  document_ids: list[uuid.UUID] | None = None) -> list[dict]:
    """Cosine-similarity search over the organization's chunks.

    The organization filter is applied *in the query*, so a bug in a caller can
    never widen the search beyond one tenant.
    """
    from pgvector.django import CosineDistance

    from apps.documents.models import DocumentChunk

    queryset = DocumentChunk.objects.filter(
        organization_id=organization_id, document__status="ready"
    )
    if document_ids:
        queryset = queryset.filter(document_id__in=document_ids)

    rows = (
        queryset.annotate(distance=CosineDistance("embedding", embedding))
        .order_by("distance")
        .select_related("document")[:top_k]
    )
    return [
        {
            "chunk_id": str(row.id),
            "document_id": str(row.document_id),
            "document_title": row.document.title,
            "chunk_index": row.chunk_index,
            "content": row.content,
            "source_label": row.source_label,
            "similarity": round(1.0 - float(row.distance), 4),
        }
        for row in rows
    ]
