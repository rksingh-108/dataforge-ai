"""WebSocket authentication.

Browsers cannot set an Authorization header on a WebSocket handshake, so the
access token is passed as a query parameter (``?token=...``) exactly once at
connect time, validated here, and never persisted. Anonymous sockets are
rejected outright — we do not accept unauthenticated connections at all.
"""
from __future__ import annotations

import urllib.parse

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _resolve_user(token: str):
    from django.contrib.auth import get_user_model
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.tokens import AccessToken

    try:
        access = AccessToken(token)
    except TokenError:
        return AnonymousUser()
    user_model = get_user_model()
    try:
        return user_model.objects.get(id=access["user_id"], is_active=True)
    except user_model.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = urllib.parse.parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [""])[0]
        scope["user"] = await _resolve_user(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)
