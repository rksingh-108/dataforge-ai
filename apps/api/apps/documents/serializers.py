"""Document serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.documents.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(
        source="uploaded_by.email", read_only=True, default=None
    )

    class Meta:
        model = Document
        fields = [
            "id", "title", "original_filename", "content_type", "size_bytes",
            "status", "error", "page_count", "chunk_count",
            "uploaded_by_email", "processed_at", "created_at",
        ]
        read_only_fields = fields


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
