"""Test settings.

The platform schema uses PostgreSQL-specific features (pgvector, JSONB,
check constraints). We therefore run tests against a **real** Postgres with the
pgvector extension rather than SQLite, so migrations and vector queries are
genuinely exercised.

Point `TEST_DATABASE_URL` at a throwaway database:
    TEST_DATABASE_URL=postgresql://dataforge:dataforge@localhost:55432/dataforge_test
The `scripts/testing/run-backend-tests.sh` helper starts one automatically.
"""
from .base import *  # noqa: F403
from .base import env, env_int

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Deterministic secrets for tests only. Never used anywhere real.
SECRET_KEY = "test-secret-key-not-for-production-use-only-0123456789"
DATAFORGE_FERNET_KEY = "S0kzq9cH6m3z8bV2Vw0i1pQ4sB7nE5tR2yU6iO9aX0M="
INTERNAL_SERVICE_TOKEN = "test-internal-service-token"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("TEST_DB_NAME", "dataforge_test"),
        "USER": env("TEST_DB_USER", "dataforge"),
        "PASSWORD": env("TEST_DB_PASSWORD", "dataforge"),
        "HOST": env("TEST_DB_HOST", "localhost"),
        "PORT": env("TEST_DB_PORT", "55432"),
        "OPTIONS": {"connect_timeout": 5},
    }
}

# Private-network data sources are allowed in tests so the host validator can be
# exercised without depending on public DNS.
DATASOURCE_ALLOW_PRIVATE_NETWORKS = False

# Tasks run inline so the pipeline is exercised, but a task failure must not
# propagate into the HTTP response (that is not what happens in production).
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {
        "auth": "1000/min",
        "analyst": "1000/min",
        "default": "1000/min",
    },
}

# AI service is never contacted in tests; tests that need it stub the client.
AI_SERVICE_URL = env("AI_SERVICE_URL", "http://ai-service.invalid")

_PG_CONN_MAX_AGE = env_int("TEST_DB_CONN_MAX_AGE", 0)
