"""Authentication for internal AI-service endpoints.

Every route except `/_health/` requires the shared service token and an explicit
organization scope. These are enforced by decorators so a new route cannot
accidentally ship unprotected.
"""
from __future__ import annotations

import functools
import hmac
import uuid

from flask import current_app, g, jsonify, request


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.message = message
        self.status = status


def _expected_token() -> str:
    return current_app.config["INTERNAL_SERVICE_TOKEN"]


def require_internal_token(view):
    """Reject any request without the exact service bearer token."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
            return jsonify({"error": {"code": "unauthorized",
                                      "message": "Service token required."}}), 401
        expected = _expected_token()
        if not expected:
            current_app.logger.error("INTERNAL_SERVICE_TOKEN is not configured.")
            return jsonify({"error": {"code": "unauthorized",
                                      "message": "Internal auth is not configured."}}), 401
        if not hmac.compare_digest(parts[1], expected):
            current_app.logger.warning("Rejected internal request with an invalid service token.")
            return jsonify({"error": {"code": "unauthorized",
                                      "message": "Invalid service token."}}), 401

        g.request_id = request.headers.get("X-Request-Id", "-")
        raw_org = request.headers.get("X-DataForge-Org", "")
        try:
            g.organization_id = str(uuid.UUID(raw_org)) if raw_org else None
        except (ValueError, TypeError):
            return jsonify({"error": {"code": "bad_request",
                                      "message": "X-DataForge-Org must be a valid UUID."}}), 400
        g.user_id = request.headers.get("X-DataForge-User", "")
        return view(*args, **kwargs)

    return wrapper


def require_organization_scope(view):
    """Ensure an organization scope is present; used by tenant-bound routes."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if not getattr(g, "organization_id", None):
            return jsonify({"error": {"code": "bad_request",
                                      "message": "X-DataForge-Org header is required."}}), 400
        return view(*args, **kwargs)

    return wrapper
