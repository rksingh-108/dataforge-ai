"""Health/readiness endpoints.

`/_health/` performs real dependency checks (database + Redis when configured).
It returns 200 only when every *required* dependency is reachable, so container
orchestrators and CI can rely on it.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

logger = logging.getLogger("apps.health")


def _check_database() -> tuple[bool, str]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, "ok"
    except Exception as exc:
        logger.error("Health check: database unreachable: %s", exc)
        return False, "unreachable"


def _check_redis() -> tuple[bool, str]:
    url = getattr(settings, "REDIS_URL", "")
    if not url:
        return True, "not-configured"
    try:
        import redis  # imported lazily so health works without the package

        client = redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return True, "ok"
    except Exception as exc:
        logger.error("Health check: redis unreachable: %s", exc)
        return False, "unreachable"


@never_cache
@require_GET
def health_view(request) -> JsonResponse:
    db_ok, db_state = _check_database()
    redis_ok, redis_state = _check_redis()
    healthy = db_ok and redis_ok
    payload = {
        "status": "ok" if healthy else "degraded",
        "service": "dataforge-api",
        "checks": {
            "database": db_state,
            "redis": redis_state,
        },
    }
    return JsonResponse(payload, status=200 if healthy else 503)
