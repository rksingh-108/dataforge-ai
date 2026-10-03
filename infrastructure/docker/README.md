# `infrastructure/docker/`

Docker build and runtime assets owned by **DevOps**.

## Status

The images are defined by per-service Dockerfiles and composed by the root
[`docker-compose.yml`](../../docker-compose.yml):

| Image | Dockerfile | Runs as | Build context |
| ----- | ---------- | ------- | ------------- |
| API + worker | [`apps/api/Dockerfile`](../../apps/api/Dockerfile) | uid 10001 | repository root |
| AI service | [`apps/ai-service/Dockerfile`](../../apps/ai-service/Dockerfile) | uid 10002 | repository root |
| Web | [`apps/web/Dockerfile`](../../apps/web/Dockerfile) | uid 10003 | repository root |

Keeping each Dockerfile next to its service means the service owner owns its
build. There is nothing shared enough to justify a separate set of build files
here, so this directory holds only documentation today.

## What belongs here

Only assets that are genuinely cross-service:

| Asset | Purpose |
| ----- | ------- |
| A shared base image | If the two Python services ever need identical OS packages, pin one base here instead of duplicating `apt-get` layers |
| `compose.override` examples | Optional local tweaks developers copy, not committed active overrides |
| Registry/CI build conventions | Documentation for multi-arch builds and image tagging |

## Invariants these images must keep

1. **Non-root.** Each service runs as a dedicated unprivileged uid.
2. **Root build context.** Dockerfiles copy `apps/<service>/` and, where needed,
   shared `scripts/`. The context is always the repository root.
3. **Healthchecks reflect readiness.** `/_health/` on api and ai-service; `pg_isready`
   on the database; `redis-cli ping` on Redis.
4. **No secrets baked in.** Configuration comes from the environment at runtime.
5. **Migrations run on API start**, idempotently, before Daphne serves traffic.

Do not add a directory of near-duplicate Dockerfiles here. If a service needs a
different image, its Dockerfile belongs beside that service.
