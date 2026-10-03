# `tests/`

Cross-service tests. Tests that live next to the code they protect are in the app
directories (`apps/api/apps/*/tests/`, `apps/ai-service/tests/`,
`apps/web/lib/*.test.ts`) — this directory holds only what genuinely spans services.

| Directory | Purpose | Runs in CI |
| --------- | ------- | ---------- |
| [`integration/`](integration/) | Checks that cross a service boundary | Partially |
| [`e2e/`](e2e/) | Drives a running stack over HTTP | **No** — see below |
| [`security/`](security/) | Points to the security suites and cross-service security checks | Yes (via `apps/api/tests/security` and the AI suites) |
| [`performance/`](performance/) | What should be measured, and how | **No** — nothing implemented |

## Current state (honest)

- **Security**: covered — 60 backend security tests (including the tenant-scope
  resolution suite and the WebSocket membership suite) plus the AI-service
  validator, host-guard and injection tests run in
  `.github/workflows/security.yml`.
- **Integration**: the API ⇄ AI-service client behaviour is covered by unit tests
  inside `apps/api/apps/ai_bridge/tests/`. This directory holds checks that need
  both services running.
- **E2E**: `e2e/smoke.sh` exists and works against a live stack. **CI does not start
  one**, so it does not run automatically (known limitation P6).
- **Performance**: nothing is implemented. **No performance claims are made
  anywhere in this repository** (P5).

## Running

```bash
# Requires a running stack: make up && make seed
bash tests/e2e/smoke.sh

# Security suites (no stack needed)
make test-security
make test-ai
```

## Adding a test here

Only add to this directory if the test **cannot** live in a single app — i.e. it
requires two or more services running, or it asserts something about the whole
system. Otherwise put it next to the code.

If you add a suite:

1. Document it in this README and in
   [`docs/testing/test-strategy.md`](../docs/testing/test-strategy.md).
2. Add a runner under `scripts/testing/`.
3. Wire it into the Makefile and into CI.
