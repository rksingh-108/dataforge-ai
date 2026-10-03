"""MySQL connector.

Read-only is enforced with `SET SESSION TRANSACTION READ ONLY` and a statement
timeout with `MAX_EXECUTION_TIME` (MySQL 5.7+/MariaDB 10.1+).
"""
from __future__ import annotations

import pymysql

from ai_service.connections.base import BaseConnector, ExternalDatabaseError

_SYSTEM_SCHEMAS = {"information_schema", "mysql", "performance_schema", "sys"}


class MySQLConnector(BaseConnector):
    engine = "mysql"

    def _connect(self):
        try:
            connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                connect_timeout=self.connect_timeout,
                read_timeout=max(5, self.statement_timeout_ms // 1000 + 5),
                write_timeout=max(5, self.statement_timeout_ms // 1000 + 5),
                charset="utf8mb4",
                ssl=self._ssl(),
                autocommit=True,
            )
        except pymysql.Error as exc:
            raise ExternalDatabaseError(
                f"Could not connect to MySQL: {self._clean(exc)}", engine=self.engine
            ) from exc

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET SESSION TRANSACTION READ ONLY")
                cursor.execute(f"SET SESSION MAX_EXECUTION_TIME={self.statement_timeout_ms}")
        except pymysql.Error as exc:
            # MAX_EXECUTION_TIME is unavailable on very old servers; read-only is
            # the critical one, so a failure here is logged via the raised error.
            connection.close()
            raise ExternalDatabaseError(
                f"Could not configure a read-only session: {self._clean(exc)}",
                engine=self.engine,
            ) from exc
        return connection

    def _ssl(self):
        if (self.config.ssl_mode or "").lower() in {"disable", "none"}:
            return None
        # PyMySQL requires explicit SSL config; a dict with verify disabled is the
        # pragmatic default for "prefer".
        if (self.config.ssl_mode or "").lower() in {"require", "verify-ca", "verify-full"}:
            return {"ssl": {}}
        return None

    def _clean(self, exc: Exception) -> str:
        message = str(exc)
        if self.config.password:
            message = message.replace(self.config.password, "***")
        return message[:300]

    def server_version(self, connection) -> str:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            row = cursor.fetchone()
        return row[0] if row else ""

    def introspect(self, connection) -> list[dict]:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_ROWS
                    FROM information_schema.TABLES
                    WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = %s
                    ORDER BY TABLE_NAME
                    """,
                    (self.config.database,),
                )
                tables = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE,
                           IS_NULLABLE, ORDINAL_POSITION, COLUMN_KEY
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                    ORDER BY TABLE_NAME, ORDINAL_POSITION
                    """,
                    (self.config.database,),
                )
                columns = cursor.fetchall()
        except pymysql.Error as exc:
            raise ExternalDatabaseError(
                f"Schema discovery failed: {self._clean(exc)}", engine=self.engine
            ) from exc

        by_table: dict[tuple[str, str], dict] = {}
        for schema, table, rows in tables:
            by_table[(schema, table)] = {
                "schema": schema,
                "name": table,
                "row_estimate": int(rows) if rows is not None else None,
                "columns": [],
            }
        for schema, table, column, data_type, nullable, position, key in columns:
            entry = by_table.get((schema, table))
            if entry is None or schema in _SYSTEM_SCHEMAS:
                continue
            entry["columns"].append(
                {
                    "name": column,
                    "data_type": data_type,
                    "nullable": nullable == "YES",
                    "primary_key": key == "PRI",
                    "position": int(position),
                }
            )
        return [by_table[key] for key in sorted(by_table)]
