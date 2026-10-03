"""Execute a *validated* read-only query against a customer database.

This module never accepts raw SQL from the model: callers must pass a
`ValidationResult` produced by `sql.validator`, which carries the rewritten query
with the row cap already applied.

Execution adds a second layer of protection on top of validation:
- the connection is opened read-only (see `connections/`),
- results are read with a hard `fetchmany(max_rows)` cap, and
- the timeout is enforced by the server.
"""
from __future__ import annotations

import contextlib
import logging
import time

from ai_service.connections.base import (
    ConnectionConfig,
    ExternalDatabaseError,
    build_connector,
)
from ai_service.sql.validator import ValidationResult

logger = logging.getLogger("ai_service.sql")


def execute_validated(
    result: ValidationResult,
    config: ConnectionConfig,
    *,
    max_rows: int = 500,
    statement_timeout_ms: int = 5000,
    allow_private_networks: bool = False,
) -> dict:
    """Run a validated query and return `{columns, rows, row_count, truncated, duration_ms}`."""
    connector = build_connector(
        config,
        connect_timeout=5,
        statement_timeout_ms=statement_timeout_ms,
        allow_private_networks=allow_private_networks,
    )

    started = time.perf_counter()
    connection = None
    try:
        connection = connector.open()
        cursor = connection.cursor()
        try:
            cursor.execute(result.safe_sql)
            columns = [description[0] for description in (cursor.description or [])]
            rows = cursor.fetchmany(max_rows + 1)
        finally:
            with contextlib.suppress(Exception):
                cursor.close()

        truncated = len(rows) > max_rows
        rows = rows[:max_rows]
        return {
            "columns": columns,
            "rows": [_jsonable(row) for row in rows],
            "row_count": len(rows),
            "truncated": truncated,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
    except ExternalDatabaseError:
        raise
    except Exception as exc:
        message = str(exc)
        if config.password:
            message = message.replace(config.password, "***")
        raise ExternalDatabaseError(
            f"Query execution failed: {message[:300]}", engine=config.engine
        ) from exc
    finally:
        if connection is not None:
            connector.close(connection)


def _jsonable(row) -> list:
    """Convert a DB row into JSON-safe values."""
    import datetime
    import decimal

    values = []
    for value in row:
        if isinstance(value, decimal.Decimal):
            values.append(float(value))
        elif isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
            values.append(value.isoformat())
        elif isinstance(value, (bytes, bytearray, memoryview)):
            values.append(f"<{len(bytes(value))} bytes>")
        else:
            values.append(value)
    return values
