"""Data source serializers.

The write-only password can be sent in, but it is **never** serialized back out.
Read serializers expose status and metadata only.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.datasources.models import DataSource, DataSourceEngine, SchemaColumn, SchemaTable


class SchemaColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemaColumn
        fields = ["column_name", "data_type", "is_nullable", "is_primary_key"]


class SchemaTableSerializer(serializers.ModelSerializer):
    columns = SchemaColumnSerializer(many=True, read_only=True)

    class Meta:
        model = SchemaTable
        fields = ["id", "schema_name", "table_name", "row_estimate", "columns"]


class DataSourceSerializer(serializers.ModelSerializer):
    """Read serializer — deliberately excludes any credential material."""

    table_count = serializers.SerializerMethodField()

    class Meta:
        model = DataSource
        fields = [
            "id", "name", "description", "engine", "host", "port", "database_name",
            "username", "ssl_mode", "is_read_only", "status", "last_error",
            "last_tested_at", "last_synced_at", "table_count", "created_at",
        ]
        read_only_fields = fields

    def get_table_count(self, obj: DataSource) -> int:
        return getattr(obj, "table_count", None) or obj.tables.count()


class DataSourceCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True,
                                        default="")
    engine = serializers.ChoiceField(choices=[e.value for e in DataSourceEngine])
    host = serializers.CharField(max_length=255)
    port = serializers.IntegerField(min_value=1, max_value=65535)
    database_name = serializers.CharField(max_length=128)
    username = serializers.CharField(max_length=128)
    password = serializers.CharField(max_length=500, write_only=True, trim_whitespace=False)
    ssl_mode = serializers.ChoiceField(
        choices=["disable", "prefer", "require", "verify-ca", "verify-full"],
        default="prefer",
    )

    def validate_name(self, value: str) -> str:
        return value.strip()


class DataSourceUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    host = serializers.CharField(max_length=255, required=False)
    port = serializers.IntegerField(min_value=1, max_value=65535, required=False)
    database_name = serializers.CharField(max_length=128, required=False)
    username = serializers.CharField(max_length=128, required=False)
    # Optional: only updated when a non-empty value is supplied.
    password = serializers.CharField(max_length=500, write_only=True, required=False,
                                     allow_blank=True, trim_whitespace=False)
    ssl_mode = serializers.ChoiceField(
        choices=["disable", "prefer", "require", "verify-ca", "verify-full"], required=False
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("No fields to update.")
        return attrs
