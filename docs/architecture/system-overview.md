# System Overview

> Audience: every engineer. Read this first.
> Related: [service-boundaries.md](service-boundaries.md), [data-flow.md](data-flow.md),
> [authentication-flow.md](authentication-flow.md), [authorization-model.md](authorization-model.md).

## 1. What DataForge AI is

DataForge AI lets an organization ask natural-language questions about its own
business data and documents, and get answers that are grounded in real sources:

- **Structured data** from connected PostgreSQL / MySQL databases, queried with
  validated, read-only SQL.
- **Unstructured data** from uploaded PDF / DOCX / TXT documents, retrieved with
  vector search (RAG).

Every AI run is recorded as an **execution** with the tools that were used, and
every security-relevant action is written to an append-only **audit log**.

## 2. Architecture in one picture

```
                          ┌──────────────────────────┐
                          │        Browser           │
                          │  Next.js (apps/web)      │
                          └───────────┬──────────────┘
                                      │ HTTPS, httpOnly session cookies (BFF)
                                      ▼
                          ┌──────────────────────────┐
                          │  Next.js server (BFF)    │
                          │  /app/api proxy routes   │
                          └───────────┬──────────────┘
                                      │ Bearer access token
                                      ▼
      ┌───────────────────────────────────────────────────────────┐
      │                Django API (apps/api)  ── modular monolith  │
      │  accounts · organizations · datasources · documents ·      │
      │  analytics(executions, audit) · common(security, crypto)   │
      │                                                            │
      │  - owns ALL platform persistence (Postgres + pgvector)     │
      │  - enforces authn, RBAC, tenant isolation                   │
      │  - orchestrates AI calls, owns execution + audit records    │
      └───────┬───────────────────────────────┬───────────────────┘
              │ SQL (psycopg)                 │ HTTP + INTERNAL_SERVICE_TOKEN
              ▼                               ▼
      ┌───────────────┐              ┌──────────────────────────────┐
      │  PostgreSQL   │              │   Flask AI service            │
      │  + pgvector   │              │   (apps/ai-service)           │
      │               │              │                               │
      │  users, orgs, │              │  providers (LLM/embeddings)   │
      │  datasources, │              │  agents (orchestrator)        │
      │  documents,   │              │  tools (registry)             │
      │  chunks,      │              │  sql (validate + execute)     │
      │  executions,  │              │  rag (chunk + embed)          │
      │  audit_logs   │              │  security (injection checks)  │
      └───────┬───────┘              └───────┬───────────────┬───────┘
              │                              │               │
              │                              │ LLM/embeddings│ read-only SQL
              ▼                              ▼               ▼
      ┌───────────────┐              ┌──────────────┐  ┌──────────────────┐
      │ Redis         │              │ LLM provider │  │ Customer         │
      │ (cache,       │              │ (config-     │  │ business DBs     │
      │  broker,      │              │  selected)   │  │ (Postgres/MySQL) │
      │  channels)    │              └──────────────┘  └──────────────────┘
      └───────┬───────┘
              │ broker
              ▼
      ┌───────────────┐
      │ Celery worker │  document processing, async jobs
      └───────────────┘
```

## 3. Component responsibilities (summary)

| Component        | Language / framework       | Owns                                                                 | Must NOT do |
| ---------------- | -------------------------- | -------------------------------------------------------------------- | ----------- |
| `apps/web`       | TypeScript, Next.js, React | UI, session cookies (BFF), presentation state                        | Business rules, direct DB access, embedding secrets in the bundle |
| `apps/api`       | Python, Django, DRF        | Domain models, authn/authz, tenancy, persistence, executions, audit  | Contain LLM/agent logic |
| `apps/ai-service`| Python, Flask              | Agent orchestration, tool registry, LLM/embedding providers, RAG chunking/embedding, SQL validation + execution | Write to the platform database, decide authorization |
| `packages/*`     | TypeScript / JSON          | Shared types, API contracts, shared config                           | Runtime business logic |
| `database/*`     | SQL + docs                 | Migrations owned by the API, seeds, fixtures, DB docs                | Application behavior |
| `infrastructure/*`| Docker, nginx, configs    | Runtime topology, health checks, deployment                          | Application logic |

## 4. Key architectural decisions

**AD-1 — Modular monolith + one dedicated AI service (not microservices).**
The domain (users, orgs, data sources, documents, executions, audit) is tightly
coupled around one database and one authorization model. Splitting it into
services would create distributed transactions with no benefit. The AI service
is separated because it has a genuinely different runtime profile (external
network calls to LLM providers and customer databases, long-running work,
independent scaling) and because AI orchestration must not be entangled with
business logic. See `service-boundaries.md`.

**AD-2 — The API is the only writer to the platform database.** The AI service
never opens a connection to the platform database. It reads data through
service-token-authenticated internal endpoints. This keeps tenant isolation,
auditing and schema ownership in one place.

**AD-3 — The AI service owns the external-DB trust boundary.** It validates and
executes read-only SQL against customer databases. Connection configuration is
fetched from the API; the AI service never stores credentials.

**AD-4 — LLM providers are configuration, not code.** `LLM_PROVIDER` selects an
implementation behind the `LLMProvider` interface. No provider is hard-coded.
(Explicitly: **no Groq**.)

**AD-5 — Tenancy is enforced in the data-access layer**, not in views. Selectors
and managers scope every query by the caller's organization.

**AD-6 — Sessions use the BFF pattern.** The browser holds only httpOnly cookies;
the Next.js server keeps tokens out of reach of JavaScript.

## 5. Non-functional targets (current, honest)

| Concern        | Target today                                                                 |
| -------------- | ---------------------------------------------------------------------------- |
| Reproducibility| `docker compose up` yields a working stack; migrations + seed are idempotent   |
| Security       | Authn/authz/tenancy enforced server-side; credentials encrypted at rest; secrets never committed |
| Testing        | Unit + API + tenant-isolation + security tests run with no external services |
| Observability  | Structured logs, health endpoints per service, executions recorded in the DB  |
| Performance    | Not benchmarked; **no performance claims are made**. See known-limitations.   |

## 6. What is intentionally out of scope

- A premium "insights/reports" generator beyond the analyst (see known limitations).
- Connectors other than PostgreSQL and MySQL.
- Multi-region deployment / HA.
- Fine-grained ABAC beyond role + organization scoping.

Honesty rule: if it is not implemented and tested, it is not described as
implemented. See [../development/known-limitations.md](../development/known-limitations.md).
