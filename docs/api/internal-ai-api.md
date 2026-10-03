# Internal API — API ⇄ AI service

Not part of the public API surface. Both directions require the shared service
token and an explicit organization scope, and every call is attributable.

## Headers (both directions)

| Header | Required | Meaning |
| ------ | -------- | ------- |
| `Authorization` | yes | `Bearer <INTERNAL_SERVICE_TOKEN>` |
| `X-DataForge-Org` | yes (except `test`/`introspect`) | Organization scope, validated as a UUID |
| `X-DataForge-User` | when acting for a user | For attribution only; never used for authorization |
| `X-Request-Id` | recommended | Correlation id, propagated to logs |

The token is compared with `hmac.compare_digest` (constant time). A missing or
mismatched token returns 401; a missing or malformed scope returns 400.

## API → AI service

Base URL: `AI_SERVICE_URL` (default `http://ai-service:8001`).

### `GET /_health/`

Unauthenticated. Returns `{status, service, checks}` where `checks` includes
whether the internal token and API base URL are configured, plus the **provider
names** (never keys). 503 when not ready.

### `POST /v1/datasources/test`

```json
{ "connection": { "engine": "postgresql", "host": "...", "port": 5432,
                  "database": "...", "username": "...", "password": "...",
                  "ssl_mode": "prefer" } }
```

Returns `{ok, server_version, error}`. `ok` is `false` with a reason on failure —
a failed connection is a normal result, not a 5xx. The host guard runs here.

### `POST /v1/datasources/introspect`

Same body. Returns `{tables: [{schema, name, row_estimate, columns: [{name,
data_type, nullable, primary_key, position}]}]}`. 422 if introspection fails.

### `POST /v1/rag/process`

```json
{ "document_id": "…", "organization_id": "…", "filename": "policy.pdf",
  "content_type": "application/pdf", "content_base64": "…" }
```

Returns `{kind, page_count, chunk_count, chunks: [{index, content, source_label,
embedding, metadata}], scan}` where `scan` reports prompt-injection flags.

Errors: 422 extraction failure, 502 embedding provider failure, 400 bad input.

### `POST /v1/embeddings/query`

```json
{ "text": "refund policy" }
```

Returns `{embedding: [...], dimensions: 1536}`.

### `POST /v1/agent/run`

```json
{
  "question": "How many orders last month?",
  "organization_id": "…",
  "datasource_ids": ["…"],
  "datasource_names": {"…": "Warehouse"},
  "document_ids": [],
  "use_documents": true,
  "execution_id": "…"
}
```

Returns `{answer, steps[], provider, model, total_tokens}` where each step is
`{index, tool, title, status, input_summary, output_summary, duration_ms, error}`.

The AI service treats `datasource_ids` as the approved set and refuses tool calls
outside it. `execution_id` is informational (the API owns the record).

Errors: 400 for a bad request, 502 when the LLM provider fails.

## AI service → API

Base URL: `INTERNAL_API_BASE_URL` (default `http://api:8000`).

### `GET /internal/datasources/{id}/connection`

Returns `{connection: {...}, is_read_only: true}` — **including the decrypted
password**, because the AI service must open the customer connection itself.

Every call writes an `AuditLog` row with action `datasource.credential_accessed`,
recording the service and the acting user. Returns 404 if the id does not belong to
the scoped organization.

### `GET /internal/datasources/{id}/schema`

Returns the cached schema (`{datasource_id, engine, tables[]}`) used to build the
SQL allowlist. Scoped to the organization; 404 otherwise.

### `POST /internal/documents/search`

```json
{ "embedding": [0.1, …], "top_k": 5, "document_ids": ["…"] }
```

Returns `{results: [{chunk_id, document_id, document_title, chunk_index, content,
source_label, similarity}]}`, filtered by organization **in the query** and limited
to documents with `status=ready`.

## Failure semantics

| Condition | AI service | API |
| --------- | ---------- | --- |
| Missing/invalid token | 401 | 401 |
| Missing/!uuid org scope | 400 | 400 |
| Resource not in scope | 404 | 404 |
| Provider failure | 502 `provider_error` | 502 `upstream_error`, execution marked `failed` |
| AI service unreachable | — | 502 `upstream_error`, execution marked `failed` |

A failed analyst run **is recorded** as a failed execution, so the failure is
visible in history rather than only in logs.

## Versioning

Paths are versioned (`/v1/…`). A breaking change to a request or response shape
requires a new version path and an updated JSON Schema in
`packages/api-contracts/`, plus a `CHANGELOG.md` entry.
