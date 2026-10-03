"""Serializers for executions and audit logs."""
from __future__ import annotations

from rest_framework import serializers

from apps.analytics.models import AuditLog, Execution, ExecutionStep


class ExecutionStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionStep
        fields = [
            "id", "index", "tool_name", "title", "status",
            "input_summary", "output_summary", "duration_ms", "error",
        ]
        read_only_fields = fields


class ExecutionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True, default=None)
    datasource_name = serializers.CharField(
        source="datasource.name", read_only=True, default=None
    )
    document_title = serializers.CharField(source="document.title", read_only=True, default=None)

    class Meta:
        model = Execution
        fields = [
            "id", "kind", "status", "question", "answer", "error",
            "user_email", "datasource_name", "document_title",
            "provider", "model_name", "total_tokens", "duration_ms",
            "started_at", "finished_at", "created_at",
        ]
        read_only_fields = fields


class ExecutionDetailSerializer(ExecutionSerializer):
    steps = ExecutionStepSerializer(many=True, read_only=True)

    class Meta(ExecutionSerializer.Meta):
        fields = [*ExecutionSerializer.Meta.fields, "steps"]
        read_only_fields = fields


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id", "action", "actor_email", "target_type", "target_id",
            "metadata", "ip_address", "request_id", "created_at",
        ]
        read_only_fields = fields


class AnalystQuerySerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000, trim_whitespace=True)
    datasource_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    use_documents = serializers.BooleanField(default=True)

    def validate_question(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Ask a more complete question.")
        return value
