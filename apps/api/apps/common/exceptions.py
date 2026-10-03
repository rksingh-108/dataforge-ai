"""Domain exceptions and the global DRF exception handler.

The handler guarantees a single error envelope shape across the API:

    {"error": {"code": "...", "message": "...", "details": {...}, "request_id": "..."}}

Internal exception text is never leaked to clients in production.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("apps.errors")


class DomainError(APIException):
    """Base class for business-rule violations raised by services."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The request could not be processed."
    default_code = "domain_error"


class NotFound(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "not_found"


class Conflict(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state."
    default_code = "conflict"


class DataSourceConnectionError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "The data source could not be reached with the supplied settings."
    default_code = "datasource_unreachable"


class UpstreamServiceError(DomainError):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "A dependent service failed to respond correctly."
    default_code = "upstream_error"


def _first_message(detail) -> str:
    if isinstance(detail, dict):
        for value in detail.values():
            return _first_message(value)
        return "Validation failed."
    if isinstance(detail, (list, tuple)) and detail:
        return _first_message(detail[0])
    return str(detail)


def dataforge_exception_handler(exc, context) -> Response | None:
    """Normalize all error responses and log server-side failures."""
    if isinstance(exc, DjangoValidationError):
        exc = DomainError(detail=getattr(exc, "messages", None) or str(exc))

    response = drf_exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if response is None:
        # Unhandled exception: log with traceback, return a generic 500.
        logger.exception("Unhandled exception: %s", exc, extra={"request_id": request_id})
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                    "details": {},
                    "request_id": request_id,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = getattr(exc, "default_code", None) or _code_for(response.status_code)
    if isinstance(exc, (PermissionDenied, Http404)):
        # Never disclose extra detail for authz/not-found.
        message = _first_message(response.data)
    else:
        message = _first_message(response.data)

    if response.status_code >= 500:
        logger.error("Server error: %s", exc, extra={"request_id": request_id})

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "details": exc.detail if isinstance(exc, DomainError) and _has_details(exc) else {},
            "request_id": request_id,
        }
    }
    return response


def _has_details(exc: DomainError) -> bool:
    return isinstance(exc.detail, dict) and bool(exc.detail)


def _code_for(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "not_authenticated",
        403: "permission_denied",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        429: "throttled",
    }.get(status_code, "error")
