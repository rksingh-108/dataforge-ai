# Onboarding — DevOps Developer

## Your area

**You own:** `infrastructure/`, `.github/workflows/`, `scripts/deployment/`, and
the Docker/compose topology. You review every change to build, CI and runtime
configuration through `CODEOWNERS`.

## What you operate

| Service | Image | Port | Health |
| ------- | ----- | ---- | ------ |
| `web` | Next.js standalone (node:22-alpine) | 3000 | `/` |
| `api` | Python 3.14 + Daphne (ASGI) | 8000 | `/_health/` |
| `ai-service` | Python 3.14 + gunicorn | 8001 | `/_health/` |
| `worker` | Same image as `api`, Celery | — | process liveness |
| `db` | `pgvector/pgvector:pg16` | 5432 | `pg_isready` |
| `redis` | `redis:7-alpine` | 6379 | `redis-cli ping` |

`api` and `worker` share a `media` volume: the worker reads documents the API wrote.

## Local operations

```bash
make up          # build and start
make seed        # development data
make logs        # tail
make ps          # status
make down        # stop
make clean       # stop and DELETE volumes
```

## CI/CD

| Workflow | Trigger | Purpose |
| -------- | ------- | ------- |
| `ci.yml` | push to `main`, PRs | Boundary checks, backend tests + Django `--deploy`, AI tests, web typecheck/tests/build, Docker image builds, compose validation |
| `security.yml` | pushes, PRs, weekly cron | Secret scan, bandit, pip-audit, npm audit, dependency review, security test suite |
| `deploy.yml` | tags, manual | Builds and publishes images; deployment is gated and **non-functional until configured** |

### The deploy workflow is intentionally inert

It publishes images, then a `deploy` job is skipped unless the repository variable
`DEPLOY_ENABLED` is `true` and an environment is configured. Nothing is deployed
anywhere today. Before enabling it you need:

1. A container registry (defaults to `ghcr.io`) and credentials.
2. An environment with deployment secrets.
3. A target: a host, a cluster, or a managed platform.
4. Health checks wired into the rollout so a bad release is caught.

See [docs/deployment/README.md](../deployment/README.md).

## Invariants you must not break

1. **Each service's healthcheck must reflect real readiness.** `/_health/`
   exercises the database and Redis; the AI service reports its configuration.
2. **Secrets come from the environment.** No secret in an image, a compose file or
   a workflow YAML. `.env` is git-ignored; CI uses repository secrets.
3. **Images build from the repository root context.** The Dockerfiles copy
   `apps/<service>/` and shared `scripts/`.
4. **Images run as non-root** (uid 10001/10002/10003).
5. **Migrations run on API start**, idempotently (`migrate --noinput`).
6. **Compose must validate in CI**: `docker compose config --quiet` with a
   throwaway `.env`.

## Environment matrix

| Variable class | Where it comes from |
| -------------- | ------------------- |
| Django + DB + Redis | `.env` / orchestration env |
| `INTERNAL_SERVICE_TOKEN` | must match on `api` and `ai-service` — deploy together |
| `DATAFORGE_FERNET_KEY` | secret; **back it up** — losing it makes stored credentials unreadable |
| LLM / embedding keys | secret; only the `ai-service` needs them |
| `API_BASE_URL` (web) | internal service address, e.g. `http://api:8000` |

## Network posture (production, recommended)

| Service | Exposure |
| ------- | -------- |
| web | Public, TLS terminated at the edge |
| api | Reachable only from `web` and `ai-service` |
| ai-service | Reachable only from `api`; **never public** — it is an egress broker |
| db, redis | Private network only |

The development compose file publishes everything for convenience. Do not copy that
to production.

## Known gaps you should pick up

- **P1** Deploy workflow does not deploy.
- **P2** No TLS/nginx configuration in the repo.
- **P3** No Kubernetes manifests.
- **P4** No observability stack — logs and health endpoints only.
- **S4** Redis has no authentication in the local stack.
- **S5** No managed secrets vault or rotation automation.
- **S7** Application-level rate limits only; no edge limiter.
- **S11** No dependency-update automation.

See [known-limitations.md](../development/known-limitations.md) and
[security/vulnerability-management/README.md](../../security/vulnerability-management/README.md).

## Testing your changes locally

```bash
docker compose build
cp .env.example .env && sed -i 's/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=local/' .env
docker compose config --quiet          # what CI runs
docker compose up -d && docker compose ps
curl -fsS localhost:8000/_health/ && curl -fsS localhost:8001/_health/
```

## Your first tasks

- Add a CI job that runs `tests/e2e/smoke.sh` against a compose stack.
- Add TLS and a reverse proxy configuration under `infrastructure/nginx/`.
- Enable grouped dependency-update PRs.
- Add a readiness gate to the deploy job so a failing healthcheck aborts a rollout.
