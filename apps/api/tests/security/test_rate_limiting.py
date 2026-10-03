"""Throttling configuration.

Exhausting a limiter in-process is flaky and slow, so these tests assert that the
canonical limits are defined, sane, and actually wired to the endpoints that need
them. The test suite relaxes the limits (see `config/settings/test.py`), which is
why the canonical values are asserted from `THROTTLE_RATES` rather than from the
active settings.
"""
from __future__ import annotations

from django.conf import settings

from apps.accounts.views import LoginView
from apps.ai_bridge.views import AnalystQueryView


def _per_minute(rate: str) -> int:
    assert rate.endswith("/min"), f"unsupported rate format: {rate}"
    return int(rate.split("/")[0])


def test_throttle_class_is_enabled():
    assert "rest_framework.throttling.ScopedRateThrottle" in settings.REST_FRAMEWORK[
        "DEFAULT_THROTTLE_CLASSES"
    ]


def test_login_is_scoped_to_the_auth_throttle():
    assert LoginView.throttle_scope == "auth"


def test_analyst_query_is_scoped_to_the_analyst_throttle():
    assert AnalystQueryView.throttle_scope == "analyst"


def test_canonical_rates_are_sane_and_ordered():
    from config.settings.base import THROTTLE_RATES

    auth = _per_minute(THROTTLE_RATES["auth"])
    analyst = _per_minute(THROTTLE_RATES["analyst"])
    default = _per_minute(THROTTLE_RATES["default"])

    # Auth must be the strictest; the default must be the loosest.
    assert auth < analyst < default
    assert auth <= 15, "login throttling should be strict"


def test_active_settings_expose_the_three_scopes():
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert {"auth", "analyst", "default"} <= set(rates)
