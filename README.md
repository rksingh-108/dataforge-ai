# DataForge AI

**DataForge AI** is a secure, AI-powered business data intelligence platform. An
organization connects approved business databases and uploads internal
documents, then asks natural-language questions that are answered by a
retrieval-augmented, tool-using AI analyst — with read-only SQL, source
citations, execution tracking and audit records.

> This repository is organized as a **modular monolith** (`apps/api`) plus a
> **dedicated AI service** (`apps/ai-service`). We deliberately avoid
> microservice sprawl. See [docs/architecture/system-overview.md](docs/architecture/system-overview.md).

---

## Quick start

Prerequisites: **Docker Desktop** with Compose v2. Everything else runs in
containers.

```bash
cp .env.example .env          # then fill in the values (a generator is in the file header)
docker compose up --build     # web :3000, api :8000, ai-service :8001
```

First run seeds a **demo organization and users** (development only) — see
[docs/development/local-setup.md](docs/development/local-setup.md) for the
credentials and what the seed actually creates.

Running services and health endpoints:

| Service    | URL                              | Health                     |
| ---------- | -------------------------------- | -------------------------- |
| Web        | http://localhost:3000            | `/`                        |
| API        | http://localhost:8000/api/v1/    | `/_health/`                |
| AI service | http://localhost:8001            | `/_health/`                |
| Postgres   | localhost:5432                   | `pg_isready` (compose)     |
| Redis      | localhost:6379                   | `redis-cli ping`           |

## The product in one screen

1. **Connect a data source** — PostgreSQL or MySQL, read-only by default,
   credentials encrypted at rest and never returned to the browser.
2. **Upload documents** — PDF, DOCX, TXT. Processed asynchronously through a
   real RAG pipeline: extraction → chunking → embeddings → pgvector.
3. **Ask the AI Analyst** — a natural-language question is routed by an agent to
   the right tool: safe read-only SQL over a connected source, or vector
   retrieval over documents. Answers cite their sources.
4. **Every AI run is tracked** — executions, tools used, and an append-only
   audit log are recorded and visible in the UI.

## Repository layout

```
apps/               Deployable applications
  web/              Next.js + React + TypeScript + Tailwind frontend
  api/              Django + DRF backend (modular monolith)
  ai-service/       Flask AI service (agents, tools, RAG, LLM abstraction)
packages/           Shared, versioned building blocks (types, contracts, config)
database/           Migrations, seeds, fixtures, database documentation
infrastructure/     Docker, nginx, redis, deployment assets
security/           Threat models, security architecture, policies, IR
docs/               Architecture, development, onboarding and operational docs
tests/              Cross-service integration, e2e, security and performance tests
scripts/            Developer, database, testing and deployment scripts
.github/            Workflows, issue/PR templates, CODEOWNERS
```

Each top-level directory has exactly one responsibility. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the ownership map.

## Documentation

| I want to…                                   | Read                                                              |
| -------------------------------------------- | ----------------------------------------------------------------- |
| Understand the architecture                  | [docs/architecture/system-overview.md](docs/architecture/system-overview.md) |
| Set up my machine                            | [docs/development/local-setup.md](docs/development/local-setup.md) |
| Know how we write code                       | [docs/development/coding-standards.md](docs/development/coding-standards.md) |
| Add my first feature                         | [docs/development/adding-a-feature.md](docs/development/adding-a-feature.md) |
| Onboard as a new developer / intern          | [docs/onboarding/new-developer.md](docs/onboarding/new-developer.md) |
| Understand my area of ownership              | [docs/onboarding/](docs/onboarding/) |
| Understand auth and authorization            | [docs/architecture/authentication-flow.md](docs/architecture/authentication-flow.md), [docs/architecture/authorization-model.md](docs/architecture/authorization-model.md) |
| Understand tenancy                           | [docs/architecture/authorization-model.md](docs/architecture/authorization-model.md) |
| Work on the AI service                       | [docs/ai/](docs/ai/) |
| Work on security                             | [security/README.md](security/README.md) |
| Contribute (branches, PRs, review)           | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Report a vulnerability                       | [SECURITY.md](SECURITY.md) |

## Engineering principles

The non-negotiables that shape every decision in this repo:

1. Modular architecture with clear ownership and strong separation of concerns.
2. Business logic lives in the backend — never in the frontend.
3. Database access is centralized in selectors/services, never scattered in views.
4. AI orchestration is isolated in `apps/ai-service`; it never touches business logic directly.
5. Tenant isolation is enforced **server-side** on every request.
6. Every important feature has tests and documentation.
7. No fake implementations, no fake API responses, no fake AI responses.
8. No hard-coded credentials, no committed secrets.
9. No giant files; no folders that exist only to look impressive.
10. Prefer a well-structured modular monolith over artificial microservices.

## Status & known limitations

This is an actively developed product. What is real, what is partial, and what is
explicitly out of scope is documented honestly in
[docs/development/known-limitations.md](docs/development/known-limitations.md).
If a capability is not listed as implemented there, assume it is not.

## License

MIT — see [LICENSE](LICENSE).
