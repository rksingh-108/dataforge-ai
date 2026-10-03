# Changelog

All notable changes to DataForge AI are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- **Tenant isolation hardened (HIGH / VM-8).** A client-supplied
  `X-Organization-Id` header was previously accepted as a tenant-scope fallback,
  widening the scoping surface. Organization scope now derives from exactly one
  place — the URL `org_id` kwarg verified against an active membership via the new
  `require_organization()` — and the header is ignored entirely. A structural guard
  in `scripts/dev/check_boundaries.py` rejects any `apps/api` code that reads the
  header or builds tenant scope from client-controlled input (headers, request
  body, query params). New regression suites cover the attack cases
  (`apps/api/tests/security/test_tenant_scope_resolution.py`, 22 cases) and the
  existing WebSocket membership checks
  (`apps/api/apps/realtime/tests/test_websocket_auth.py`, 6 cases, closing VM-9).

### Added

- **Engineering foundation (Phase 1)** — repository structure, architecture
  documentation, development standards, Git/PR workflow, ownership model,
  onboarding paths, testing and security strategy, and the Definition of Done.
- **Core platform (Phase 2)** — custom email-based user model, organizations,
  memberships and a code-defined RBAC matrix; JWT authentication with rotating and
  blacklisted refresh tokens; password change that revokes every session; an
  append-only audit log; server-enforced tenant isolation.
- **Data intelligence foundation (Phase 3)** — data-source records for PostgreSQL
  and MySQL with Fernet-encrypted credentials that are never serialized;
  connection testing and schema introspection performed by the AI service;
  SSRF-aware host validation at create and connect time.
- **AI + RAG (Phase 4)** — a dedicated Flask AI service with a configuration-driven
  `LLMProvider`/`EmbeddingProvider` abstraction (OpenAI-compatible, Anthropic,
  Azure OpenAI, Ollama — no vendor hard-coded, and explicitly no Groq); a bounded
  agent loop with a tool registry; AST-level read-only SQL validation with row
  caps, timeouts, allowlisting and forbidden-function rejection; a real RAG
  pipeline (extract → chunk → embed → pgvector) with Celery-driven asynchronous
  processing; prompt-injection detection and untrusted-content delimiting.
- **Product experience (Phase 5)** — Next.js application shell with a BFF session
  layer (tokens in httpOnly cookies), permission-aware navigation, and pages for
  the dashboard, AI Analyst, data sources, documents, execution history and
  detail, audit logs, users/roles and settings, each with loading, empty and error
  states.
- **Security, QA and DevOps (Phase 6)** — GitHub Actions workflows (`ci.yml`,
  `security.yml`, `deploy.yml`), Dockerfiles and a Compose stack with real health
  checks, security test suites for tenancy, authorization, headers and throttling,
  and a full security documentation set (threat models, architecture, policies,
  vulnerability management, incident response, access control, secrets management,
  security testing).
- **Company environment finalization (Phase 7)** — honest limitations inventory,
  boundary enforcement in CI, and documentation reconciled with the implementation.

### Added

- **Windows developer entry points `START.bat` / `STOP.bat`** at the repository
  root: one command starts the whole Compose stack (with readiness waits and local
  URLs), one stops it without deleting volumes or development data. Documented in
  [docs/development/local-setup.md](docs/development/local-setup.md).

### Fixed

- **The Celery `worker` was reported unhealthy.** It shares the API image, whose
  healthcheck curls the API's HTTP port; Celery serves no HTTP, so the worker
  would show `unhealthy` forever and a readiness-gated orchestrator would reject a
  perfectly healthy stack. The Compose `worker` service now checks the worker over
  Celery itself (`celery -A config inspect ping`).
- **The E2E smoke test asserted the wrong thing.** It expected `200` from the web
  root, which correctly returns `307` for an unauthenticated visitor; the check now
  follows the redirect. `tests/e2e/smoke.sh` runs green (16/16) against a locally
  started stack.
- **API image and CI could not install or boot.** `apps/api/requirements/base.txt`
  omitted `channels`, `channels-redis`, `daphne` and `pgvector` — packages the
  code imports and that `INSTALLED_APPS`/`config/asgi.py` require. Any clean
  install — the Docker image, CI, a new developer — failed to start. They are now
  declared.
- **Lint was non-deterministic and failing.** Ruff 0.16 enables 413 rules by
  default (up from 59), and the repository had no configuration, so `ruff check`
  failed with 185 findings on a clean checkout. An explicit `pyproject.toml` now
  pins the enforced rule set so a Ruff upgrade cannot silently change CI.
- **Frontend dependency audit failed.** `npm audit --audit-level=high` reported a
  critical `vitest` advisory, a high `vite` advisory and vulnerable PostCSS copies
  bundled inside Next.js. The test toolchain was upgraded (Vitest 4, Vite 8,
  jsdom 30) and PostCSS is pinned to a patched version via an npm override; the
  audit now reports zero vulnerabilities and the frontend build is unchanged.
- **The security scan could not fail the build.** `security.yml` ran bandit with
  `|| true`, so a real finding would not have blocked a merge. The scan now runs
  against a documented `pyproject.toml` config and is enforcing.
- **Python version drift.** CI pinned 3.13 while the images run 3.14; both are now
  3.14, matching the Ruff target.

### Security

- Data-source credentials are encrypted at rest and are never returned to a client.
- Every internal call to the AI service requires a shared service token and an
  explicit organization scope; credential retrieval is audited on every call.
- Model-authored SQL is validated by an AST-level parser and executed on a
  database session that is read-only at the engine level.

### Known limitations

See [docs/development/known-limitations.md](docs/development/known-limitations.md)
for the complete, maintained list. Highlights:

- The browser-side WebSocket client is not wired up; the server-side consumer,
  JWT middleware and broadcasting are implemented.
- No MFA, SSO or email-based password reset.
- No antivirus scanning on uploads; no CSP header.
- The deploy workflow publishes images but deploys nowhere until configured.
- No performance benchmarks exist, and no performance claims are made.

---

## How to maintain this file

- Add entries under `Unreleased` in the **same pull request** as the change.
- Group under `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
- Write for a reader who did not see the PR: what changed for *them*.
- On release, move `Unreleased` content under a new version heading with the date.
