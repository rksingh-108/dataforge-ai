# Onboarding — QA Developer

## Your area

**You own:** the test strategy, the test suites across all services, and
`tests/` at the repository root (integration, e2e, security, performance).

You do not own the code under test. When you find a bug, you write the test that
proves it and either fix it or hand it to the owning team with the failing test.

## What exists today

| Suite | Location | Command | Count |
| ----- | -------- | ------- | ----- |
| Backend unit/API | `apps/api/apps/*/tests/` | `make test-backend` | 102 |
| Backend security | `apps/api/tests/security/` | `make test-security` | 30 |
| AI service (incl. SQL safety, injection, host guard) | `apps/ai-service/tests/` | `make test-ai` | 94 |
| Frontend unit | `apps/web/lib/*.test.ts` | `make test-web` | 15 |

All of these run in CI on every pull request.

## What does **not** exist yet (be honest about it)

- **No end-to-end suite running in CI.** `tests/e2e/smoke.sh` exists and works, but
  CI does not start the stack to run it (known limitation P6).
- **No performance/load tests.** `tests/performance/` describes what should be
  measured; nothing is implemented, and no performance claims are made.
- **No contract tests** between the API and the AI service beyond the unit-level
  client tests.
- **No cross-service integration suite in CI** (known limitation P6).

Closing these gaps is the highest-value work available in this area.

## Set up

```bash
make test            # everything
make up && make seed # a running stack for exploratory testing
```

## Testing principles

1. **Test behaviour, not implementation.** Assert on the API contract and the UX,
   not on which internal function ran.
2. **Only stub true external boundaries** — LLM vendors and customer databases.
   Stubbing the component under test proves nothing.
3. **A test that cannot fail is not a test.** Verify it fails without the fix.
4. **Security tests are named after the attack.** See
   [security/security-testing/README.md](../../security/security-testing/README.md).
5. **Deterministic and fast.** No sleeps, no reliance on wall-clock ordering, no
   network in unit tests.
6. **One reason to change per test.** Use `parametrize` for matrices.

## Critical flows to protect

These must always have coverage. If you add a regression here, it is a priority.

1. Login, refresh rotation, logout, password change (session lifecycle).
2. Tenant isolation on every org-scoped resource.
3. RBAC: each role denied what it should be denied.
4. Data-source create → credential encryption → connection test → schema sync.
5. Document upload → validation rejection cases → RAG pipeline → vector search.
6. Analyst query → execution and step records → failure handling.
7. SQL validator: writes, DDL, multi-statement, unknown tables, system tables,
   dangerous functions, locking.
8. Internal endpoints: token required, org scope enforced, credential access audited.

## Writing an E2E test

`tests/e2e/smoke.sh` is the pattern: it drives the real stack over HTTP and fails
on any unexpected status. Extend it rather than writing a parallel harness, and
record the result in the script's output so CI can display it.

```bash
make up && make seed
bash tests/e2e/smoke.sh
```

## Your first tasks

- Wire `tests/e2e/smoke.sh` into CI behind a compose profile (closes P6).
- Add the missing WebSocket membership test (VM-9).
- Add a contract test that fails if the AI service's response shape drifts.
- Measure and record baseline latency for the analyst flow — then we can talk about
  performance with numbers instead of adjectives.

## Ask about

- A failing behaviour you are unsure is a bug → the owning team, with the failing
  test and the request id.
- Anything security-shaped → security owner. Do not write a detailed public issue
  describing an exploitable weakness.
