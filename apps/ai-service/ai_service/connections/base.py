"""Connector base: configuration, read-only sessions, and the factory.

Every connection is opened with:
- a short connect timeout,
- an explicit statement timeout, and
- a **read-only session** enforced by the database itself (not just by our SQL
  validation). Even if a bug let a write statement through, the engine would
  refuse it.
"""
from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any

from ai_service.security.host_guard import HostNotAllowed, assert_host_allowed


class ExternalDatabaseError(RuntimeError):
    """A safe-to-display error from a customer database interaction."""

    def __init__(self, message: str, *, engine: str = "", detail: dict | None = None):
        super().__init__(message)
        self.engine = engine
        self.detail = detail or {}


@dataclass
class ConnectionConfig:
    engine: str
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str = "prefer"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConnectionConfig:
        try:
            host = str(data["host"]).strip()
            database = str(data["database"]).strip()
            username = str(data["username"])
        except (KeyError, TypeError) as exc:
            raise ExternalDatabaseError("Incomplete connection configuration.") from exc

        engine = str(data.get("engine", "")).lower()
        if engine not in {"postgresql", "mysql"}:
            raise ExternalDatabaseError(f"Unsupported engine '{engine}'.")
        try:
            port = int(data["port"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ExternalDatabaseError("A valid port is required.") from exc

        return cls(
            engine=engine,
            host=host,
            port=port,
            database=database,
            username=username,
            password=str(data.get("password", "")),
            ssl_mode=str(data.get("ssl_mode", "prefer") or "prefer"),
        )


class BaseConnector:
    engine: str = ""

    def __init__(self, config: ConnectionConfig, *, connect_timeout: int = 5,
                 statement_timeout_ms: int = 5000, allow_private_networks: bool = False):
        self.config = config
        self.connect_timeout = connect_timeout
        self.statement_timeout_ms = statement_timeout_ms
        self.allow_private_networks = allow_private_networks

    # --- Interface ---------------------------------------------------------
    def open(self):
        """Open a connection configured for read-only use with a timeout."""
        self._guard_host()
        return self._connect()

    def close(self, connection) -> None:
        # Closing is best-effort; a failure here must not mask the real result.
        with contextlib.suppress(Exception):
            connection.close()

    def server_version(self, connection) -> str:
        raise NotImplementedError

    def introspect(self, connection) -> list[dict]:
        raise NotImplementedError

    # --- Helpers -----------------------------------------------------------
    def _guard_host(self) -> None:
        try:
            assert_host_allowed(self.config.host, allow_private=self.allow_private_networks)
        except HostNotAllowed as exc:
            raise ExternalDatabaseError(str(exc), engine=self.engine) from exc

    def _connect(self):  # pragma: no cover - implemented by subclasses
        raise NotImplementedError


def build_connector(config: ConnectionConfig, **kwargs) -> BaseConnector:
    if config.engine == "postgresql":
        from ai_service.connections.postgres import PostgresConnector

        return PostgresConnector(config, **kwargs)
    if config.engine == "mysql":
        from ai_service.connections.mysql import MySQLConnector

        return MySQLConnector(config, **kwargs)
    raise ExternalDatabaseError(f"Unsupported engine '{config.engine}'.")


def test_connection(config: ConnectionConfig, *, connect_timeout: int = 5,
                    statement_timeout_ms: int = 5000,
                    allow_private_networks: bool = False) -> dict:
    """Open a real connection, run a trivial query, and report the result."""
    connector = build_connector(
        config,
        connect_timeout=connect_timeout,
        statement_timeout_ms=statement_timeout_ms,
        allow_private_networks=allow_private_networks,
    )
    connection = None
    try:
        connection = connector.open()
        version = connector.server_version(connection)
        return {"ok": True, "server_version": version, "error": ""}
    except ExternalDatabaseError as exc:
        return {"ok": False, "server_version": "", "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "server_version": "", "error": _safe_driver_message(exc, config)}
    finally:
        if connection is not None:
            connector.close(connection)


def introspect_schema(config: ConnectionConfig, *, connect_timeout: int = 5,
                      statement_timeout_ms: int = 10000,
                      allow_private_networks: bool = False) -> dict:
    """Return `{tables: [...]}` for a live database."""
    connector = build_connector(
        config,
        connect_timeout=connect_timeout,
        statement_timeout_ms=statement_timeout_ms,
        allow_private_networks=allow_private_networks,
    )
    connection = None
    try:
        connection = connector.open()
        return {"tables": connector.introspect(connection)}
    finally:
        if connection is not None:
            connector.close(connection)


def _safe_driver_message(exc: Exception, config: ConnectionConfig) -> str:
    """Never echo the password, even if a driver includes it in the message."""
    message = str(exc)
    if config.password:
        message = message.replace(config.password, "***")
    return message[:500]
