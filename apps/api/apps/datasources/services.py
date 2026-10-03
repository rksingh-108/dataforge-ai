"""Services for data sources.

The API owns the *record* of a data source; the AI service owns the *network
egress* to it. Connection testing and schema introspection are therefore
delegated to the AI service over the internal API, never performed here.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.ai_bridge.client import AIServiceClient
from apps.analytics.services import record_audit
from apps.common.exceptions import DataSourceConnectionError
from apps.datasources.models import (
    DataSource,
    DataSourceStatus,
    SchemaColumn,
    SchemaTable,
)
from apps.datasources.validators import validate_host, validate_port

logger = logging.getLogger("apps.datasources")


@transaction.atomic
def create_datasource(
    *,
    organization,
    actor,
    name: str,
    engine: str,
    host: str,
    port: int,
    database_name: str,
    username: str,
    password: str,
    description: str = "",
    ssl_mode: str = "prefer",
) -> DataSource:
    # Reject dangerous outbound targets before we store anything.
    validate_host(host)
    validate_port(port)

    datasource = DataSource(
        organization=organization,
        name=name.strip(),
        description=description.strip(),
        engine=engine,
        host=host.strip(),
        port=port,
        database_name=database_name.strip(),
        username=username.strip(),
        ssl_mode=ssl_mode,
        is_read_only=True,
        created_by=actor,
    )
    datasource.set_password(password)
    datasource.save()

    record_audit(
        organization=organization,
        actor=actor,
        action="datasource.created",
        target_type="datasource",
        target_id=str(datasource.id),
        metadata={"engine": engine, "host": host, "database": database_name},
    )
    return datasource


@transaction.atomic
def update_datasource(*, datasource: DataSource, actor, **changes) -> DataSource:
    if "password" in changes:
        password = changes.pop("password")
        if password:
            datasource.set_password(password)
    if changes.get("host"):
        validate_host(changes["host"])
    for field, value in changes.items():
        if value is not None and hasattr(datasource, field):
            setattr(datasource, field, value)

    # Any change to connection settings invalidates the tested status.
    datasource.status = DataSourceStatus.UNKNOWN
    datasource.save()
    record_audit(
        organization=datasource.organization,
        actor=actor,
        action="datasource.updated",
        target_type="datasource",
        target_id=str(datasource.id),
        metadata={"fields": sorted(changes.keys())},
    )
    return datasource


@transaction.atomic
def delete_datasource(*, datasource: DataSource, actor) -> None:
    organization = datasource.organization
    datasource_id = str(datasource.id)
    name = datasource.name
    datasource.delete()
    record_audit(
        organization=organization,
        actor=actor,
        action="datasource.deleted",
        target_type="datasource",
        target_id=datasource_id,
        metadata={"name": name},
    )


def test_connection(*, datasource: DataSource, actor, client: AIServiceClient | None = None) -> dict:
    """Ask the AI service to open a real connection. Updates status accordingly."""
    client = client or AIServiceClient()
    config = datasource.connection_config()
    try:
        result = client.test_connection(config)
    except DataSourceConnectionError:
        raise
    except Exception as exc:
        datasource.status = DataSourceStatus.ERROR
        datasource.last_error = str(exc)[:1000]
        datasource.last_tested_at = timezone.now()
        datasource.save(update_fields=["status", "last_error", "last_tested_at", "updated_at"])
        record_audit(
            organization=datasource.organization, actor=actor,
            action="datasource.test_failed", target_type="datasource",
            target_id=str(datasource.id), metadata={"reason": str(exc)[:200]},
        )
        raise DataSourceConnectionError(str(exc)) from exc

    ok = bool(result.get("ok"))
    datasource.status = DataSourceStatus.CONNECTED if ok else DataSourceStatus.ERROR
    datasource.last_error = "" if ok else str(result.get("error", ""))[:1000]
    datasource.last_tested_at = timezone.now()
    datasource.save(update_fields=["status", "last_error", "last_tested_at", "updated_at"])

    record_audit(
        organization=datasource.organization, actor=actor,
        action="datasource.tested", target_type="datasource",
        target_id=str(datasource.id), metadata={"ok": ok, "server_version": result.get("server_version", "")},
    )
    return result


@transaction.atomic
def sync_schema(*, datasource: DataSource, actor,
                client: AIServiceClient | None = None) -> dict:
    """Discover tables/columns from the live database and cache them.

    The previous metadata is replaced atomically so a failure never leaves a
    half-updated schema visible.
    """
    client = client or AIServiceClient()
    try:
        result = client.introspect(datasource.connection_config())
    except Exception as exc:
        record_audit(
            organization=datasource.organization, actor=actor,
            action="datasource.schema_sync_failed", target_type="datasource",
            target_id=str(datasource.id), metadata={"reason": str(exc)[:200]},
        )
        raise DataSourceConnectionError(str(exc)) from exc

    tables = result.get("tables", [])
    SchemaTable.objects.filter(datasource=datasource).delete()
    created_tables = 0
    created_columns = 0
    for table in tables:
        table_row = SchemaTable.objects.create(
            datasource=datasource,
            schema_name=table.get("schema", "public"),
            table_name=table["name"],
            row_estimate=table.get("row_estimate"),
        )
        created_tables += 1
        columns = [
            SchemaColumn(
                table=table_row,
                column_name=col["name"],
                data_type=col.get("data_type", "unknown"),
                is_nullable=bool(col.get("nullable", True)),
                is_primary_key=bool(col.get("primary_key", False)),
                ordinal_position=int(col.get("position", 0)),
            )
            for col in table.get("columns", [])
        ]
        SchemaColumn.objects.bulk_create(columns)
        created_columns += len(columns)

    datasource.last_synced_at = timezone.now()
    datasource.status = DataSourceStatus.CONNECTED
    datasource.last_error = ""
    datasource.save(update_fields=["last_synced_at", "status", "last_error", "updated_at"])

    record_audit(
        organization=datasource.organization, actor=actor,
        action="datasource.schema_synced", target_type="datasource",
        target_id=str(datasource.id),
        metadata={"tables": created_tables, "columns": created_columns},
    )
    return {"tables": created_tables, "columns": created_columns}
