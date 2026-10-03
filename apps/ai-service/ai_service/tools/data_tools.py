"""Data tools: schema inspection and read-only SQL execution.

Both tools re-derive the allowlist from the platform API and validate before any
socket is opened. A tool never trusts an id it was not given.
"""
from __future__ import annotations

import logging

from ai_service.connections.base import ConnectionConfig, ExternalDatabaseError
from ai_service.sql.executor import execute_validated
from ai_service.sql.validator import SQLValidationError, validate_read_only_query
from ai_service.tools.registry import ToolContext, ToolError

logger = logging.getLogger("ai_service.tools.data")

# How many rows to hand back to the model. The full result is capped by the
# validator/executor; this keeps prompt sizes bounded.
MODEL_ROW_LIMIT = 50
MODEL_COLUMN_LIMIT = 40


def _assert_allowed_datasource(context: ToolContext, datasource_id: str) -> None:
    if not datasource_id:
        raise ToolError("datasource_id is required.")
    if context.datasource_ids and datasource_id not in context.datasource_ids:
        raise ToolError("That data source is not part of this conversation's approved scope.")


def list_tables(context: ToolContext, datasource_id: str) -> dict:
    _assert_allowed_datasource(context, datasource_id)
    try:
        schema = context.api_client.get_schema(datasource_id)
    except Exception as exc:
        raise ToolError(f"Could not load the data source schema: {str(exc)[:200]}") from exc

    tables = schema.get("tables", [])
    context.allowed_tables[datasource_id] = {
        f"{t.get('schema', 'public')}.{t['name']}" for t in tables
    }
    return {
        "datasource_id": datasource_id,
        "table_count": len(tables),
        "tables": [
            {
                "name": t["name"],
                "schema": t.get("schema", "public"),
                "columns": [
                    {"name": c["column_name"], "type": c["data_type"]}
                    for c in t.get("columns", [])[:MODEL_COLUMN_LIMIT]
                ],
            }
            for t in tables
        ],
    }


def run_sql(context: ToolContext, datasource_id: str, sql: str, purpose: str = "") -> dict:
    _assert_allowed_datasource(context, datasource_id)

    allowed = context.allowed_tables.get(datasource_id)
    if not allowed:
        try:
            schema = context.api_client.get_schema(datasource_id)
        except Exception as exc:
            raise ToolError(f"Could not load the data source schema: {str(exc)[:200]}") from exc
        allowed = {f"{t.get('schema', 'public')}.{t['name']}" for t in schema.get("tables", [])}
        context.allowed_tables[datasource_id] = allowed

    try:
        connection = context.api_client.get_connection(datasource_id)
    except Exception as exc:
        raise ToolError(f"Could not load connection settings: {str(exc)[:200]}") from exc

    config = ConnectionConfig.from_dict(connection)
    settings = context.settings

    try:
        validated = validate_read_only_query(
            sql,
            engine=config.engine,
            allowed_tables=allowed,
            max_rows=settings.sql_max_rows,
            max_joins=settings.sql_max_joins,
        )
    except SQLValidationError as exc:
        # Surface the reason to the model so it can correct itself. This is safe:
        # the message never contains data, only a rule violation.
        return {
            "ok": False,
            "rejected": True,
            "reason": str(exc),
            "code": exc.code,
        }

    try:
        outcome = execute_validated(
            validated,
            config,
            max_rows=settings.sql_max_rows,
            statement_timeout_ms=settings.sql_statement_timeout_ms,
            allow_private_networks=settings.allow_private_networks,
        )
    except ExternalDatabaseError as exc:
        return {"ok": False, "reason": str(exc)[:300]}

    return {
        "ok": True,
        "purpose": purpose[:200],
        "datasource_id": datasource_id,
        "tables": validated.tables,
        "columns": outcome["columns"],
        "rows": outcome["rows"][:MODEL_ROW_LIMIT],
        "row_count": outcome["row_count"],
        "truncated": outcome["truncated"] or outcome["row_count"] > MODEL_ROW_LIMIT,
        "duration_ms": outcome["duration_ms"],
    }
