"""Request correlation id middleware."""
from __future__ import annotations

import uuid

from apps.common.logging import set_request_id


class RequestIdMiddleware:
    """Attach a correlation id to every request and log record.

    Honours an inbound ``X-Request-Id`` (so a trace can span web -> api -> ai
    service) but only if it looks like a UUID, to avoid header injection into
    logs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-Id", "")
        try:
            request_id = str(uuid.UUID(incoming))
        except (ValueError, TypeError):
            request_id = str(uuid.uuid4())
        request.request_id = request_id
        set_request_id(request_id)
        response = self.get_response(request)
        response["X-Request-Id"] = request_id
        return response
