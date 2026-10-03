"""Authentication for service-to-service (internal) endpoints.

The AI service authenticates with a shared bearer token (``INTERNAL_SERVICE_TOKEN``)
compared in constant time. Internal endpoints are not part of the public API and
must additionally declare an organization scope via ``X-DataForge-Org``.
"""
from __future__ import annotations

import hmac
import logging
import uuid

from django.conf import settings
from rest_framework import authentication, exceptions

logger = logging.getLogger("apps.security.internal")


class ServiceTokenAuthentication(authentication.BaseAuthentication):
    """Authenticate a machine caller via the shared internal service token."""

    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword.lower().encode():
            raise exceptions.AuthenticationFailed("Service token required.")

        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Malformed service Authorization header.")

        supplied = header[1].decode()
        expected = getattr(settings, "INTERNAL_SERVICE_TOKEN", "")
        if not expected:
            logger.error("Internal endpoint called but INTERNAL_SERVICE_TOKEN is not configured.")
            raise exceptions.AuthenticationFailed("Internal authentication is not configured.")

        if not hmac.compare_digest(supplied, expected):
            logger.warning("Rejected internal request with an invalid service token.")
            raise exceptions.AuthenticationFailed("Invalid service token.")

        # Service callers are not users. We return a lightweight principal and
        # rely on the explicit org header (validated by the view) for scoping.
        return (ServicePrincipal(), None)


class ServicePrincipal:
    """Minimal principal representing the AI service; never treated as a user."""

    is_authenticated = True
    is_anonymous = False
    is_service = True
    pk = None

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return "service:ai"


def require_organization_scope(request) -> uuid.UUID:
    """Read and validate ``X-DataForge-Org`` on an internal request."""
    raw = request.headers.get("X-DataForge-Org", "")
    try:
        return uuid.UUID(raw)
    except (ValueError, TypeError) as exc:
        raise exceptions.ParseError("X-DataForge-Org must be a valid organization id.") from exc
