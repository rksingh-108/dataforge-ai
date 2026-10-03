# Test Strategy

## Principles

1. **Test behaviour, not implementation.** Assert on contracts and outcomes.
2. **Stub only true external boundaries.** LLM vendors and customer databases are
   stubbed; the validator, tenancy, permissions and the agent loop are not.
3. **A test that cannot fail is not a test.** Verify it fails before the fix.
4. **Fast and deterministic.** No sleeps, no wall-clock ordering, no network in
   unit tests.
5. **Security tests are named after the attack.**
6. **Critical flows always have coverage**, even as the code changes.

## The pyramid (as implemented)

```
                 E2E (tests/e2e)          1 shell script, requires a live stack
              Integration                  API ⇄ AI-service client tests
          API / application                 130 backend tests (70 app + 60 security)
       Unit + security                      94 AI + 60 security + 15 web
```

| Suite | Location | Command | Count |
| ----- | -------- | ------- | ----- |
| Backend app/unit | `apps/api/apps/*/tests/` | `make test-backend` | 70 |
| Backend cross-cutting security | `apps/api/tests/security/` | `make test-security` | 60 |
| WebSocket membership | `apps/api/apps/realtime/tests/` | `make test-security` | 6 |
| AI service | `apps/ai-service/tests/` | `make test-ai` | 94 |
| Frontend unit | `apps/web/lib/*.test.ts` | `make test-web` | 15 |
| End-to-end smoke | `tests/e2e/smoke.sh` | `bash tests/e2e/smoke.sh` | manual/CI-pending |

## Frameworks

| Layer | Tool |
| ----- | ---- |
| Python | pytest + pytest-django + pytest-cov |
| Frontend | Vitest + Testing Library |
| Lint | Ruff (Python), `tsc --noEmit` (TypeScript) |
| Static security | bandit, pip-audit, npm audit |

## Databases in tests

Backend tests run against **real PostgreSQL with pgvector**. The schema uses vector
columns, partial unique constraints and JSONB, so SQLite would hide real bugs.
`make test-backend` starts a throwaway `pgvector/pgvector:pg16` container on port
55432 and removes it afterwards (or uses `TEST_DB_*` if set).

There is no SQLite path, by design. See known limitation D5.

## Fixtures

`apps/api/conftest.py` provides `organization`, `auth_client`, `make_member`,
`client_for`, `api_client` and file fixtures. Authentication uses **real JWTs**
rather than `force_authenticate`, so the token pipeline is covered.

`apps/ai-service/tests/conftest.py` builds the Flask app with an explicit `Settings`
object and swaps in deterministic test doubles, so no test depends on the
environment.

## What must be covered for a new feature

| Requirement | Test to add |
| ----------- | ----------- |
| New endpoint | Happy path + a permission failure |
| New tenant-owned resource | A cross-tenant denial (404) |
| New permission | A row in `apps/api/tests/security/test_authorization_matrix.py` |
| New SQL validation rule | A case in `apps/ai-service/tests/test_sql_validator.py` |
| New tool | A scope-violation test in `test_tools.py` |
| New upload path | Rejection cases (type, magic bytes, size, duplicate) |
| New provider | A registry selection test |

## Coverage

CI enforces a **70% floor** in both Python services. Coverage is a floor, not a
goal: a well-tested critical path matters more than a high global number. Security
and tenancy paths are expected to be fully covered regardless of the total.

## What is not tested (honest)

- **No E2E suite runs in CI** (known limitation P6). `tests/e2e/smoke.sh` works
  locally against a running stack.
- **No performance benchmarks** (P5). No performance claims are made.
- **No contract tests** between the API and the AI service beyond client-level tests.
- **WebSocket consumer membership check** is covered by
  `apps/api/apps/realtime/tests/test_websocket_auth.py` (connect, forged org,
  non-member, cross-group isolation); the browser-side client remains unwired
  (known limitation U1).
- **No visual regression tests.**

## Adding a test suite

If you introduce a new suite, do all four:

1. Add it to the table above.
2. Add a runner under `scripts/testing/`.
3. Wire it into `Makefile`.
4. Add it to `.github/workflows/ci.yml` (or `security.yml` for security suites).
