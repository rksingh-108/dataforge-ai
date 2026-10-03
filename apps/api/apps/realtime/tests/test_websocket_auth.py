"""WebSocket authorization tests for the execution consumer.

The socket is server-push only, but the *connect* path is a security boundary: it
authenticates the JWT and re-checks organization membership before the socket is
added to an organization's broadcast group. These tests drive the real ASGI
application through Channels' ``WebsocketCommunicator`` — the authentication
middleware, the membership check and group scoping all run for real.

Two details worth knowing:

* ``transaction=True`` is required because the consumer resolves the user and the
  membership on a separate database connection; a wrapped test transaction would
  be invisible to it.
* Tokens are minted in the synchronous test body, never inside the coroutine,
  because building a token touches the database.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.rbac import Role
from apps.organizations.models import Membership, Organization
from config.asgi import application

User = get_user_model()

pytestmark = pytest.mark.django_db(transaction=True)

RECEIVE_TIMEOUT = 0.5


@pytest.fixture
def tenants(transactional_db):
    """An owner of Acme and an owner of Globex — one socket-worthy user each."""
    acme_owner = User.objects.create_user(
        email="ws-acme@example.com", password="CorrectHorse9!", full_name="Acme Owner"
    )
    globex_owner = User.objects.create_user(
        email="ws-globex@example.com", password="CorrectHorse9!", full_name="Globex Owner"
    )
    acme = Organization.objects.create(name="Acme", slug="acme-ws", created_by=acme_owner)
    Membership.objects.create(organization=acme, user=acme_owner, role=Role.OWNER.value)
    globex = Organization.objects.create(name="Globex", slug="globex-ws", created_by=globex_owner)
    Membership.objects.create(organization=globex, user=globex_owner, role=Role.OWNER.value)
    return SimpleNamespace(
        acme=acme, globex=globex, acme_owner=acme_owner, globex_owner=globex_owner
    )


def _token(user) -> str:
    """Mint an access token. Must run in a synchronous context."""
    return str(RefreshToken.for_user(user).access_token)


def _path(org_id, token: str | None = None) -> str:
    base = f"/ws/orgs/{org_id}/executions/"
    return f"{base}?token={token}" if token else base


def _run(scenario):
    return async_to_sync(scenario)()


# --- Positive -----------------------------------------------------------------

def test_member_connects_and_is_confirmed(tenants):
    token = _token(tenants.acme_owner)
    org_id = str(tenants.acme.id)

    async def scenario():
        communicator = WebsocketCommunicator(application, _path(org_id, token))
        connected, _ = await communicator.connect()
        assert connected is True

        message = await communicator.receive_json_from(timeout=RECEIVE_TIMEOUT)
        assert message["type"] == "connected"
        assert message["organization_id"] == org_id

        await communicator.disconnect()

    _run(scenario)


# --- Negative: authentication -------------------------------------------------

def test_missing_token_is_rejected(tenants):
    org_id = str(tenants.acme.id)

    async def scenario():
        communicator = WebsocketCommunicator(application, _path(org_id))
        connected, code = await communicator.connect()
        assert connected is False
        assert code == 4401

    _run(scenario)


def test_invalid_token_is_rejected(tenants):
    org_id = str(tenants.acme.id)

    async def scenario():
        communicator = WebsocketCommunicator(application, _path(org_id, "not-a-real-token"))
        connected, code = await communicator.connect()
        assert connected is False
        assert code == 4401

    _run(scenario)


# --- Negative: tenancy --------------------------------------------------------

def test_non_member_cannot_connect_to_another_organizations_channel(tenants):
    """Acme's owner, authenticated, asking for Globex's channel."""
    token = _token(tenants.acme_owner)
    org_id = str(tenants.globex.id)

    async def scenario():
        communicator = WebsocketCommunicator(application, _path(org_id, token))
        connected, code = await communicator.connect()
        assert connected is False
        assert code == 4403

    _run(scenario)


def test_forged_organization_id_cannot_bypass_membership(tenants):
    """The organization id is client-supplied in the URL, so it must be verified
    against membership — a non-member is closed out with 4403."""
    token = _token(tenants.globex_owner)  # valid token, wrong organization
    org_id = str(tenants.acme.id)

    async def scenario():
        communicator = WebsocketCommunicator(application, _path(org_id, token))
        connected, code = await communicator.connect()
        assert connected is False
        assert code == 4403

    _run(scenario)


def test_a_member_of_one_org_gets_only_that_orgs_events(tenants):
    """Both users connect to their own organization; a broadcast to one group must
    never reach the other socket."""
    acme_token = _token(tenants.acme_owner)
    globex_token = _token(tenants.globex_owner)
    acme_org = str(tenants.acme.id)
    globex_org = str(tenants.globex.id)

    async def scenario():
        layer = get_channel_layer()

        acme_socket = WebsocketCommunicator(application, _path(acme_org, acme_token))
        globex_socket = WebsocketCommunicator(application, _path(globex_org, globex_token))

        assert (await acme_socket.connect())[0] is True
        assert (await acme_socket.receive_json_from(timeout=RECEIVE_TIMEOUT))["type"] == "connected"
        assert (await globex_socket.connect())[0] is True
        assert (await globex_socket.receive_json_from(timeout=RECEIVE_TIMEOUT))["type"] == "connected"

        # An event for Globex must reach Globex and not Acme.
        await layer.group_send(
            f"org.{globex_org}.executions",
            {"type": "execution_event",
             "payload": {"type": "execution.updated", "id": "globex-event"}},
        )
        assert (await globex_socket.receive_json_from(timeout=RECEIVE_TIMEOUT))["id"] == "globex-event"
        assert await acme_socket.receive_nothing(timeout=RECEIVE_TIMEOUT) is True

        # And the reverse.
        await layer.group_send(
            f"org.{acme_org}.executions",
            {"type": "execution_event",
             "payload": {"type": "execution.updated", "id": "acme-event"}},
        )
        assert (await acme_socket.receive_json_from(timeout=RECEIVE_TIMEOUT))["id"] == "acme-event"
        assert await globex_socket.receive_nothing(timeout=RECEIVE_TIMEOUT) is True

        await acme_socket.disconnect()
        await globex_socket.disconnect()

    _run(scenario)
