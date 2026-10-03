"""PostgreSQL connector.

Read-only is enforced at the *session* level via
`default_transaction_read_only=on`, and a `statement_timeout` is set server-side.
Both mean a runaway or malicious query is stopped by Postgres, not by us.
"""
from __future__ import annotations

import psycopg

from ai_service.connections.base import BaseConnector, ExternalDatabaseError

_SYSTEM_SCHEMAS = ("pg_catalog", "information_schema")


class PostgresConnector(BaseConnector):
    engine = "postgresql"

    def _ssl_mode(self):
        # psycopg accepts the libpq sslmode string directly.
        return self.config.ssl_mode or "prefer"

    def _connect(self):
        try:
            return psycopg.connect(
                host=self.config.host,
                port=self.config.port,
                dbname=self.config.database,
                user=self.config.username,
                password=self.config.password,
                connect_timeout=self.connect_timeout,
                sslmode=self._ssl_mode(),
                options=(
                    f"-c statement_timeout={self.statement_timeout_ms} "
                    "-c default_transaction_read_only=on"
                ),
            )
        except psycopg.Error as exc:
            raise ExternalDatabaseError(
                f"Could not connect to PostgreSQL: {self._clean(exc)}",
                engine=self.engine,
            ) from exc

    def _clean(self, exc: Exception) -> str:
        message = str(exc)
        if self.config.password:
            message = message.replace(self.config.password, "***")
        return message[:300]

    def server_version(self, connection) -> str:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            row = cursor.fetchone()
        return (row[0] if row else "").split(",")[0]

    def introspect(self, connection) -> list[dict]:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                      AND table_schema <> ALL(%s)
                    ORDER BY table_schema, table_name
                    """,
                    (list(_SYSTEM_SCHEMAS),),
                )
                tables = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT c.table_schema, c.table_name, c.column_name,
                           c.data_type, c.is_nullable, c.ordinal_position,
                           (pk.column_name IS NOT NULL) AS is_primary_key
                    FROM information_schema.columns c
                    LEFT JOIN (
                        SELECT tc.table_schema, tc.table_name, kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON tc.constraint_name = kcu.constraint_name
                         AND tc.table_schema = kcu.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                    ) pk ON pk.table_schema = c.table_schema
                        AND pk.table_name = c.table_name
                        AND pk.column_name = c.column_name
                    WHERE c.table_schema <> ALL(%s)
                    ORDER BY c.table_schema, c.table_name, c.ordinal_position
                    """,
                    (list(_SYSTEM_SCHEMAS),),
                )
                columns = cursor.fetchall()
        except psycopg.Error as exc:
            raise ExternalDatabaseError(
                f"Schema discovery failed: {self._clean(exc)}", engine=self.engine
            ) from exc

        return _assemble(tables, columns)


def _assemble(table_rows, column_rows) -> list[dict]:
    by_table: dict[tuple[str, str], dict] = {}
    for schema, table in table_rows:
        by_table[(schema, table)] = {
            "schema": schema,
            "name": table,
            "row_estimate": None,
            "columns": [],
        }
    for schema, table, column, data_type, nullable, position, is_pk in column_rows:
        entry = by_table.get((schema, table))
        if entry is None:
            continue
        entry["columns"].append(
            {
                "name": column,
                "data_type": data_type,
                "nullable": nullable == "YES",
                "primary_key": bool(is_pk),
                "position": int(position),
            }
        )
    return [by_table[key] for key in sorted(by_table)]
