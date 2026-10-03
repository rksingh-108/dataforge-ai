# `@dataforge/api-contracts`

Machine-readable JSON Schemas for the boundary between the Django API and the
Flask AI service. Owned jointly by the AI and backend teams.

## Why schemas here (and types elsewhere)

`packages/shared-types` covers the browser-facing shapes in TypeScript. The API ⇄
AI-service boundary is crossed by two different languages and two different teams,
so it needs a language-neutral, machine-checkable contract. That is what lives
here.

The human-readable description of the same endpoints is in
[`docs/api/internal-ai-api.md`](../../docs/api/internal-ai-api.md). The schemas and
the documentation must agree; a change to one requires a change to the other.

## Schemas

| File | Endpoint | Direction |
| ---- | -------- | --------- |
| `agent-run.request.json` | `POST /v1/agent/run` | API → AI service |
| `agent-run.response.json` | `POST /v1/agent/run` | AI service → API |
| `internal-datasource-connection.response.json` | `GET /internal/datasources/{id}/connection` | API → AI service |

Additional schemas are added as endpoints stabilise. There is no code generation:
the schemas exist to be reviewed, version-controlled and used by tests.

## Rules

1. **Additive changes are preferred.** Adding an optional field is safe; removing or
   retyping one is breaking.
2. **Breaking changes need a version bump** (`/v2/...`) plus a `CHANGELOG.md` entry.
3. **`additionalProperties: false`** on request schemas: an unexpected field is a
   bug, and silently ignoring it hides mistakes.
4. **Credential-bearing schemas are marked as such** in their description, and their
   endpoint must be audited.
5. **The contract does not describe authorization.** Authorization happens in the
   API before the call; the AI service treats the scope it is given as already
   authorized.

## Validating locally

The schemas are plain JSON Schema (draft 2020-12). To check a payload:

```bash
python - <<'PY'
import json, jsonschema
schema = json.load(open("packages/api-contracts/schemas/agent-run.request.json"))
payload = {"question": "How many orders?", "organization_id": "11111111-1111-1111-1111-111111111111"}
jsonschema.validate(payload, schema)
print("contract OK")
PY
```

`jsonschema` is not a runtime dependency; install it ad hoc when you need to check
something. Wiring contract validation into the test suites is a tracked
improvement (see [docs/testing/test-strategy.md](../../docs/testing/test-strategy.md)).
