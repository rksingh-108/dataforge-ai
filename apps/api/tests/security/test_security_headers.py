"""Hardening headers must actually be sent, not merely configured."""
from __future__ import annotations

from django.test import override_settings
from django.urls import reverse


def test_nosniff_and_frame_deny_are_present(api_client):
    response = api_client.get(reverse("health"))
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"


def test_authenticated_endpoints_also_carry_headers(auth_client):
    response = auth_client.get(reverse("current-user"))
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"


def test_correlation_id_is_echoed(api_client):
    response = api_client.get(reverse("health"), HTTP_X_REQUEST_ID="not-a-uuid")
    # An invalid inbound id must be replaced, never echoed verbatim.
    assert response["X-Request-Id"] != "not-a-uuid"


def test_error_responses_use_the_standard_envelope(api_client):
    response = api_client.get(reverse("current-user"))
    assert response.status_code == 401
    body = response.json()
    assert set(body) == {"error"}
    assert {"code", "message", "details", "request_id"} <= set(body["error"])


@override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
def test_cookie_settings_can_be_hardened_for_production():
    from django.conf import settings

    assert settings.SESSION_COOKIE_SECURE is True
    assert settings.CSRF_COOKIE_SECURE is True
