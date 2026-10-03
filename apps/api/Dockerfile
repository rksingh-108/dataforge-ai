# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# DataForge AI — API (Django modular monolith, ASGI via Daphne for Channels)
# Build context: repository root (see docker-compose.yml).
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libpq is required by psycopg at runtime; curl is used by the healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY apps/api/requirements/base.txt apps/api/requirements/base.txt
RUN pip install --no-cache-dir -r apps/api/requirements/base.txt

COPY apps/api/ apps/api/
COPY scripts/ scripts/

WORKDIR /app/apps/api

# Run as a non-root user.
RUN useradd --create-home --uid 10001 dataforge \
    && chown -R dataforge:dataforge /app
USER dataforge

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/_health/ || exit 1

# Daphne serves ASGI (HTTP + WebSocket). Migrations run in the entrypoint.
CMD ["sh", "-c", "python manage.py migrate --noinput && daphne -b 0.0.0.0 -p 8000 config.asgi:application"]
