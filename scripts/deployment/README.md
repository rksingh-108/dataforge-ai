# `scripts/deployment/`

Release and rollout helpers owned by **DevOps**. See
[`docs/deployment/README.md`](../../docs/deployment/README.md) for the full
process and the pre-flight checklist.

## Status

**Empty by design.** Nothing here is executed by CI yet, because the deploy
workflow (`.github/workflows/deploy.yml`) builds and publishes images but deploys
nowhere until a target environment is configured — known limitation **P1**. A
placeholder script that "deploys" would be a fake implementation, so none is
shipped.

## What belongs here

Small, single-purpose scripts that the release process will call. Each must be
idempotent, print what it does, and exit non-zero on failure:

| Helper | Responsibility |
| ------ | -------------- |
| `migrate.sh` | Apply migrations against a target environment, before any rollout |
| `rollout.sh` | Roll the api → worker → ai-service → web images to a given tag |
| `smoke.sh` | Hit `/_health/` on api and ai-service, then a real login, and fail the release on any non-200 |
| `rollback.sh` | Return to the previous image tag and apply the reverse migration if one shipped |

## Conventions

Follow the rules in [`../README.md`](../README.md): bash for orchestration, Python
for anything with real logic, `set -euo pipefail`, secrets read from the
environment, and no secret ever written to disk. Reuse
`tests/e2e/smoke.sh` rather than duplicating its checks.

## Enabling the pipeline

Before these scripts can be wired into `deploy.yml`:

1. Choose a container registry and a target environment.
2. Store deployment credentials as environment secrets (never in the repo).
3. Wire `/_health/` into the rollout so a bad release aborts.
4. Flip the `DEPLOY_ENABLED` repository variable and remove the inert `deploy`
   job's placeholder steps.
