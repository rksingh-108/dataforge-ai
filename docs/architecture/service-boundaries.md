# Service Boundaries

This document is the contract between teams. If a change would cross a boundary
described here, it needs an architecture review (see [CONTRIBUTING.md](../../CONTRIBUTING.md)).

## 1. Allowed dependencies

```
web  ──HTTP──▶  api  ──HTTP──▶  ai-service
                 │                  │
                 ▼                  ▼
            Postgres+pgvector   external business DBs + LLM providers
```

- `web` may call `api` (through its BFF proxy) and nothing else.
- `api` may call `ai-service` and its own database. It may **not** implement
  agent/LLM logic.
- `ai-service` may call LLM/embedding providers, external business databases,
  and `api`'s internal endpoints. It may **not** connect to the platform database.
- Nothing calls back into `web`.

Reverse dependencies (e.g. `api` importing from `ai-service` in-process, or the
AI service importing Django models) are forbidden.

## 2. Interface contracts

The API ↔ AI-service boundary is HTTP/JSON and is versioned under `/v1`.
Request/response shapes are documented in
[../api/internal-ai-api.md](../api/internal-ai-api.md) and mirrored as JSON
Schemas under `packages/api-contracts/`.

Every internal call must carry:

| Header                 | Meaning                                         |
| ---------------------- | ----------------------------------------------- |
| `Authorization`        | `Bearer <INTERNAL_SERVICE_TOKEN>`               |
| `X-DataForge-Org`      | Organization id the call is scoped to           |
| `X-DataForge-User`     | Acting user id (for attribution in the AI layer)|
| `X-Request-Id`         | Correlation id, propagated to logs and audit    |

The AI service treats `X-DataForge-Org` as an already-authorized scope: the API
has *already* checked the user's membership and permission before calling. The AI
service still uses it to scope retrieval so it can never leak across tenants.

## 3. Internal endpoints (API → AI service)

| Method | Path                        | Purpose                                     |
| ------ | --------------------------- | ------------------------------------------- |
| GET    | `/v1/health`                | Liveness/readiness                          |
| POST   | `/v1/agent/run`             | Run the AI analyst for one question         |
| POST   | `/v1/rag/process`           | Extract + chunk + embed a document          |
| POST   | `/v1/embeddings/query`      | Embed a retrieval query                     |

Internal endpoints (AI service → API), protected by the same service token:

| Method | Path                                       | Purpose                                    |
| ------ | ------------------------------------------ | ------------------------------------------ |
| GET    | `/internal/datasources/<id>/connection`    | Decrypted connection config (audited)      |
| POST   | `/internal/documents/search`               | pgvector similarity search scoped by org   |

These internal endpoints are registered on the API under the `/internal/`
prefix and are **not** part of the public API surface (`/api/v1/`). They reject
any request without a valid service token, and they log a warning if called from
a non-private network in production.

## 4. Ownership map

| Area                        | Owner        | Directories |
| --------------------------- | ------------ | ----------- |
| Web / UI                    | Frontend     | `apps/web`, `packages/shared-types` (frontend usage) |
| API / domain                | Backend      | `apps/api` |
| AI / LLM / RAG              | AI           | `apps/ai-service`, `packages/api-contracts` |
| Schema / migrations / seeds | Data         | `database`, `apps/api/**/migrations` |
| Infra / CI-CD               | DevOps       | `infrastructure`, `.github`, `scripts/deployment` |
| Security controls & tests   | Security     | `security`, `tests/security`, `apps/api/**/security` |
| Test strategy & coverage    | QA           | `tests`, per-app test dirs |

`CODEOWNERS` turns this table into enforced review requirements.

## 5. Boundary rules that are tested

These rules are not just prose; they are enforced by checks in CI:

- `apps/api` must not import the `flask` package — see
  `scripts/dev/check_boundaries.py`.
- `apps/ai-service` must not import `django` — same script.
- `apps/web` must not contain a database driver dependency — checked against
  `apps/web/package.json`.
- `apps/api` must not read the client-controlled `X-Organization-Id` header for
  authorization — same script. Organization scope comes from the URL route plus a
  verified membership (see [authorization-model.md](authorization-model.md)).
- A tenant-scoped selector/service call must not receive an organization id taken
  from `kwargs`, `query_params` or `request.data`. Use
  `require_organization(request)`; same script.
