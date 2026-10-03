# Integration Tests

Tests that cross a service boundary, or that need two or more services running.

## What exists today

The API ⇄ AI-service boundary is covered by **client-level tests inside the API**,
which is where the boundary is enforced:

| Test | Covers |
| ---- | ------ |
| `apps/api/apps/ai_bridge/tests/test_analyst.py` | Request shape sent to the AI service, execution and step recording, failure handling, datasource-id filtering |
| `apps/api/apps/ai_bridge/tests/test_internal_endpoints.py` | Service-token enforcement, org scoping, credential disclosure to the AI service, auditing, vector search scoping |
| `apps/api/apps/datasources/tests/test_datasources.py` | Delegation of connection testing and introspection to the AI service |

Those tests stub only the *network call* (`AIServiceClient`). Everything else —
authorization, tenancy, persistence, auditing, the response shape — is real.

## What is not covered here yet

- The AI service processing a **real** request from the API process (HTTP-level),
  which would catch a header or JSON-shape drift that client mocks hide.
- Contract validation of payloads against `packages/api-contracts/schemas/`.

Both are worth adding. The contract schemas already exist; wiring them into a test
is a small, high-value task.

## Running

```bash
make test-integration     # currently runs the API-side boundary tests
```

For a true cross-service run, start the stack and use
[`../e2e/smoke.sh`](../e2e/smoke.sh).

## Writing one

Prefer an in-process test that stubs the network if it can prove the property. Only
reach for a live stack when the thing under test **is** the transport.

When you do write a live one:

1. Start the stack in the test (`docker compose up -d` or a fixture).
2. Wait for `/_health/` on both services rather than sleeping.
3. Tear the stack down on exit, including on failure (`trap`).
4. Assert on the API contract, not on internal implementation.
