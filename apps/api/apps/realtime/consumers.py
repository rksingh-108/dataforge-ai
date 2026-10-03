"""WebSocket consumer for live execution status.

A socket is only accepted when the authenticated user has an active membership in
the organization in the URL path. The membership is re-checked at connect time
(not trusted from the token), and the group name is derived from the *verified*
organization id.
"""
from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ExecutionConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        self.org_id = self.scope["url_route"]["kwargs"]["org_id"]
        user = self.scope.get("user")

        if user is None or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return
        if not await self._is_member(user, self.org_id):
            # Same code as unauthenticated: do not reveal org existence.
            await self.close(code=4403)
            return

        self.group_name = f"org.{self.org_id}.executions"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected", "organization_id": self.org_id})

    async def disconnect(self, code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs) -> None:
        # The channel is server-push only; we accept a ping for liveness.
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def execution_event(self, event: dict) -> None:
        await self.send_json(event["payload"])

    @database_sync_to_async
    def _is_member(self, user, org_id: str) -> bool:
        from apps.organizations.selectors import get_active_membership

        try:
            return get_active_membership(user=user, organization_id=org_id) is not None
        except (ValueError, TypeError):
            return False
