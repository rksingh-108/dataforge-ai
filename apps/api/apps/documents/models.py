"""Document and chunk models.

Chunks carry a pgvector embedding so retrieval happens in the database the API
owns. The embedding dimension is configuration-driven (`EMBEDDING_DIM`); changing
it requires a migration (vector columns are fixed-width).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.common.models import BaseModel, OrganizationScopedModel

EMBEDDING_DIM = int(getattr(settings, "EMBEDDING_DIM", 1536))


def document_upload_path(instance, filename: str) -> str:
    """Store uploads under an org/document-scoped path (no user-supplied names)."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"documents/{instance.organization_id}/{instance.id}.{extension}"


class DocumentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class Document(OrganizationScopedModel):
    title = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=128)
    size_bytes = models.PositiveBigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    file = models.FileField(upload_to=document_upload_path)

    status = models.CharField(
        max_length=16, choices=DocumentStatus.choices, default=DocumentStatus.PENDING
    )
    error = models.TextField(blank=True)
    page_count = models.PositiveIntegerField(default=0)
    chunk_count = models.PositiveIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="documents_uploaded",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["organization", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "checksum_sha256"],
                condition=~models.Q(checksum_sha256=""),
                name="unique_document_checksum_per_org",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_ready(self) -> bool:
        return self.status == DocumentStatus.READY


class DocumentChunk(BaseModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    # Denormalized for fast, safe tenant scoping of vector search.
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="document_chunks"
    )
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    char_count = models.PositiveIntegerField(default=0)
    source_label = models.CharField(max_length=200, blank=True)
    embedding = VectorField(dimensions=EMBEDDING_DIM)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["document", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"], name="unique_chunk_index_per_document"
            ),
        ]
        indexes = [
            models.Index(fields=["organization"]),
            HnswIndex(
                name="document_chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document_id}#{self.chunk_index}"

    def set_embedding(self, values: list[float]) -> None:
        if len(values) != EMBEDDING_DIM:
            raise ValueError(
                f"Embedding has {len(values)} dimensions; expected {EMBEDDING_DIM}."
            )
        self.embedding = values
