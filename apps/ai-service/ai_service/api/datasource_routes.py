"""Connection testing and schema introspection.

These routes are the only place the AI service opens a connection on behalf of the
platform, so they are the authoritative egress point (host guard runs here).
"""
from __future__ import annotations

import logging

from flask import Blueprint, current_app, jsonify, request

from ai_service.api import error_response
from ai_service.connections.base import (
    ConnectionConfig,
    ExternalDatabaseError,
    introspect_schema,
    test_connection,
)
from ai_service.security.internal_auth import require_internal_token

bp = Blueprint("datasources", __name__, url_prefix="/v1/datasources")
logger = logging.getLogger("ai_service.api.datasources")


class _ConfigError(Exception):
    """Carries a ready-made error response out of the config parser."""

    def __init__(self, response):
        super().__init__("invalid connection config")
        self.response = response


def _config_from_request() -> ConnectionConfig:
    """Parse and validate the connection object, or raise `_ConfigError`."""
    payload = request.get_json(silent=True) or {}
    connection = payload.get("connection")
    if not isinstance(connection, dict):
        raise _ConfigError(error_response("bad_request", "`connection` must be an object."))
    try:
        return ConnectionConfig.from_dict(connection)
    except ExternalDatabaseError as exc:
        raise _ConfigError(error_response("invalid_connection", str(exc), 400)) from exc


@bp.post("/test")
@require_internal_token
def test_datasource_connection():
    try:
        config = _config_from_request()
    except _ConfigError as exc:
        return exc.response
    result = test_connection(
        config,
        connect_timeout=current_app.config["SQL_CONNECT_TIMEOUT_SECONDS"],
        statement_timeout_ms=current_app.config["SQL_STATEMENT_TIMEOUT_MS"],
        allow_private_networks=current_app.config["ALLOW_PRIVATE_NETWORKS"],
    )
    # A failed connection test is a valid result, not a transport error, so the
    # HTTP status is 200 either way and `ok` is carried in the body.
    return jsonify(result), 200


@bp.post("/introspect")
@require_internal_token
def introspect_datasource():
    try:
        config = _config_from_request()
    except _ConfigError as exc:
        return exc.response
    try:
        result = introspect_schema(
            config,
            connect_timeout=current_app.config["SQL_CONNECT_TIMEOUT_SECONDS"],
            statement_timeout_ms=max(current_app.config["SQL_STATEMENT_TIMEOUT_MS"], 10000),
            allow_private_networks=current_app.config["ALLOW_PRIVATE_NETWORKS"],
        )
    except ExternalDatabaseError as exc:
        return error_response("introspection_failed", str(exc)[:300], 422)
    logger.info("Introspected %s tables from %s", len(result["tables"]), config.engine)
    return jsonify(result)
