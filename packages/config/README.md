# `@dataforge/config`

Shared **non-secret** configuration: canonical tool versions, port assignments and
environment conventions.

## What lives here

- `tooling-versions.json` — Python, Node, Postgres and Redis versions, and the port
  map. CI and the scripts read these so a local run matches the pipeline.
- Conventions documented below, in one place rather than repeated per service.

## What must never live here

- **Secrets.** No keys, tokens, passwords or connection strings. Ever. This
  directory is committed and world-readable.
- **Environment-specific values.** A hostname, a vendor account or a region is
  deployment configuration, not shared config.
- **Business rules.** Anything that makes a decision belongs in a service.

## Environment conventions

| Variable | Convention |
| -------- | ---------- |
| `*_URL` | Full URL including scheme |
| `*_HOST_PORT` | Host-side published port for local Compose only |
| `*_TTL_*` | Duration; the unit is in the name (`JWT_ACCESS_TTL_MINUTES`) |
| `NEXT_PUBLIC_*` | Visible to the browser — **never put a secret here** |
| `DATAFORGE_*` | Product-specific settings |
| `LLM_*`, `EMBEDDING_*` | Provider selection and credentials (secrets: values come from the environment, never from this package) |

Everything is documented in [`.env.example`](../../.env.example), which is the
single source of truth. Adding a variable means adding it there.

## Ports

| Service | Port | Host port override |
| ------- | ---- | ------------------ |
| Web | 3000 | `WEB_HOST_PORT` |
| API | 8000 | `API_HOST_PORT` |
| AI service | 8001 | `AI_SERVICE_HOST_PORT` |
| Postgres | 5432 | `POSTGRES_HOST_PORT` |
| Redis | 6379 | `REDIS_HOST_PORT` |

The test database container uses **55432** so it never collides with a local
Postgres on 5432.

## Why a package for this

These values were previously duplicated in compose files, the Makefile and CI, and
drifted. One file, read by all three, is cheaper than the drift.
