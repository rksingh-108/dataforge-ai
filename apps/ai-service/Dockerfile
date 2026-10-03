# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# DataForge AI — AI service (Flask, agents/tools/RAG)
# Build context: repository root.
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY apps/ai-service/requirements/base.txt apps/ai-service/requirements/base.txt
RUN pip install --no-cache-dir -r apps/ai-service/requirements/base.txt

COPY apps/ai-service/ apps/ai-service/

WORKDIR /app/apps/ai-service

RUN useradd --create-home --uid 10002 dataforge \
    && chown -R dataforge:dataforge /app
USER dataforge

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8001/_health/ || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8001", "--workers", "2", "--threads", "4", \
     "--timeout", "180", "--access-logfile", "-", "wsgi:app"]
