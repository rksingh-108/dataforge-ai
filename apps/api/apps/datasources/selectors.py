"""Selectors for data sources (always org-scoped)."""
from __future__ import annotations

import uuid

from django.db.models import QuerySet

from apps.datasources.models import DataSource, SchemaTable


def list_datasources(*, organization_id: uuid.UUID) -> QuerySet[DataSource]:
    return DataSource.objects.filter(organization_id=organization_id).order_by("name")


def get_datasource(*, organization_id: uuid.UUID, datasource_id: uuid.UUID) -> DataSource | None:
    return DataSource.objects.filter(id=datasource_id, organization_id=organization_id).first()


def list_tables(*, datasource_id: uuid.UUID) -> QuerySet[SchemaTable]:
    return (
        SchemaTable.objects.filter(datasource_id=datasource_id)
        .prefetch_related("columns")
        .order_by("schema_name", "table_name")
    )


def allowed_table_names(*, datasource_id: uuid.UUID) -> set[str]:
    """Fully-qualified table names the SQL safety layer may reference."""
    return {
        f"{schema}.{table}"
        for schema, table in SchemaTable.objects.filter(datasource_id=datasource_id).values_list(
            "schema_name", "table_name"
        )
    }
