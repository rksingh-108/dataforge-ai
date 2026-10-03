# Deployment

## Current state — read this first

The repository contains everything needed to **build and run** the stack, and the
`deploy.yml` workflow **builds and publishes images**. It does **not deploy
anywhere**: the deploy job is gated behind the repository variable
`DEPLOY_ENABLED` and is inert by default. No target environment is configured.

This is stated plainly rather than implied. See known limitation P1.

## Topology

| Service | Image | Port | Notes |
| ------- | ----- | ---- | ----- |
| web | `apps/web/Dockerfile` | 3000 | Next.js standalone; the only public surface |
| api | `apps/api/Dockerfile` | 8000 | Daphne (ASGI: HTTP + WebSocket); runs migrations on start |
| worker | same image as api | — | Celery; shares the `media` volume with api |
| ai-service | `apps/ai-service/Dockerfile` | 8001 | **Never expose publicly** — it is an egress broker |
| db | `pgvector/pgvector:pg16` | 5432 | Private |
| redis | `redis:7-alpine` | 6379 | Private; set `requirepass` in production |

Recommended production topology: a reverse proxy terminates TLS for `web` and
`api`; `ai-service`, `db` and `redis` are on a private network with no public
ingress.

## Required configuration

Everything in `.env.example`. The values that must be **generated and kept secret**:

| Variable | Notes |
| -------- | ----- |
| `DJANGO_SECRET_KEY` | ≥ 40 chars; the API refuses to boot in production otherwise |
| `DATAFORGE_FERNET_KEY` | **Back it up.** Losing it makes stored credentials unreadable |
| `INTERNAL_SERVICE_TOKEN` | ≥ 32 chars; must be identical on api and ai-service |
| `LLM_API_KEY` / `EMBEDDING_API_KEY` | Only the ai-service needs them |
| `POSTGRES_PASSWORD` | |
| `CSRF_TRUSTED_ORIGINS` | The public web origin; required in production |

Production settings **fail fast** (`config/settings/production.py`) when the secret
key is short, the Fernet key is missing, the service token is short, or
`CSRF_TRUSTED_ORIGINS` is empty. A misconfigured deployment does not start.

## Deployment checklist

- [ ] Secrets generated and stored in a secret manager (not a file on disk)
- [ ] `DJANGO_SETTINGS_MODULE=config.settings.production`
- [ ] `DEBUG=false`; `DJANGO_ALLOWED_HOSTS` set to real hostnames
- [ ] `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS` set to the real origin
- [ ] TLS terminated at the edge; `DJANGO_SECURE_SSL_REDIRECT=true`
- [ ] `api`, `ai-service`, `db`, `redis` not reachable from the internet
- [ ] Redis requires authentication and is on a private network
- [ ] `DATASOURCE_ALLOW_PRIVATE_NETWORKS=false` unless a private path exists
- [ ] Database backups configured and a restore tested
- [ ] `media` volume is persistent and included in backups
- [ ] Health checks wired to the orchestrator: `/_health/` on api and ai-service
- [ ] Logs shipped somewhere durable, with the correlation id preserved
- [ ] Alerting on `/_health/` failures and on 5xx rates
- [ ] Migration step is separate from, and ordered before, the rollout
- [ ] Rollback plan: previous image tag and a reversible migration

## Build

```bash
docker build -f apps/api/Dockerfile       -t dataforge/api:$(git rev-parse --short HEAD) .
docker build -f apps/ai-service/Dockerfile -t dataforge/ai-service:$(git rev-parse --short HEAD) .
docker build -f apps/web/Dockerfile       -t dataforge/web:$(git rev-parse --short HEAD) .
```

All three use the **repository root** as the build context.

## Release process

1. Merge to `main`; CI must be green.
2. Tag: `git tag v1.2.0 && git push --tags`.
3. `deploy.yml` builds and publishes the images tagged with the version.
4. Deploy: run migrations, then roll out api → worker → ai-service → web.
5. Verify: `/_health/` on api and ai-service, then a real login and a real analyst
   query against a staging data source.
6. Update `CHANGELOG.md` (move `Unreleased` under the version heading) before the
   tag, not after.

## Rollback

1. Revert to the previous image tag.
2. Apply the reverse migration if the release included one.
3. Confirm `/_health/` and a login.

Reverse migrations are only safe if the migration was written to be reversible —
that is part of the review checklist.

## Environment variables reference

See [`.env.example`](../../.env.example) for the complete list with comments. It is
the single source of truth for configuration; if you add a variable, add it there.

## Not implemented

- Kubernetes manifests or Helm charts (P3).
- TLS certificate management and reverse-proxy config in-repo (P2).
- Metrics, tracing, dashboards (P4).
- Automated backups and retention policy (D1, D2).
- Blue/green or canary rollout.
