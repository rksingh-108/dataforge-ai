# Agent Tools

Tools are the only way the agent can affect the world. Each declares a JSON schema
(given to the model) and a handler (called by us). Handlers receive a
`ToolContext` carrying the **already-authorized** organization scope — never raw
request data.

## `list_tables`

Inspect the tables and columns of an approved data source. The agent must call this
before writing SQL, because the validator only allows discovered tables.

```json
{ "datasource_id": "uuid" }
```

Returns `{datasource_id, table_count, tables: [{name, schema, columns: [{name,
type}]}]}` (columns truncated to 40 per table for prompt size).

Side effect: caches the allowlist on the tool context for this run.

## `run_sql`

Run **one** read-only SELECT against an approved data source.

```json
{ "datasource_id": "uuid", "sql": "SELECT …", "purpose": "Short description" }
```

Returns on success:

```json
{ "ok": true, "purpose": "…", "datasource_id": "…", "tables": ["public.orders"],
  "columns": ["id","total"], "rows": [[1, 12.5]], "row_count": 1,
  "truncated": false, "duration_ms": 8 }
```

Returns a **rejection** the model can learn from (not an exception):

```json
{ "ok": false, "rejected": true, "reason": "Table 'secret' is not part of this data source's discovered schema.", "code": "sql_unknown_table" }
```

Safety applied on every call (see
[security/threat-model/sql-injection.md](../../security/threat-model/sql-injection.md)):

1. `datasource_id` must be in the run's approved set.
2. Schema allowlist fetched from the API (tenant-scoped).
3. Connection settings fetched from the API (audited).
4. AST validation: single statement, read-only SELECT, no DDL/DML, no locking, no
   forbidden functions, tables allowlisted, join limit.
5. Row cap applied by **wrapping** the query.
6. Executed on a read-only session with a server-enforced statement timeout.
7. At most 50 rows are returned to the model.

## `search_documents`

Search the organization's uploaded documents for relevant passages.

```json
{ "query": "refund policy", "top_k": 5 }
```

Returns `{query, match_count, content_scan, passages: [{document_id,
document_title, source_label, similarity, content}]}`.

`content_scan` reports prompt-injection flags found in the retrieved passages
(`{flagged, categories, count}`). Flagged content is still returned — it is data,
and the model is instructed to treat it as such — but the flag is recorded on the
execution step and visible in the UI.

The embedding is produced by the configured embedding provider; the vector search
runs in the API, filtered by organization and restricted to `status=ready`
documents.

## Adding a tool

1. Implement the handler in `tools/`, raising `ToolError` for safe failures.
2. Register it in `build_default_registry()` with a clear description and a strict
   JSON schema (`additionalProperties: false`).
3. Assert scope inside the handler if it touches tenant data.
4. Add tests to `apps/ai-service/tests/test_tools.py` — including an out-of-scope
   argument case.
5. Document it here and add a `CHANGELOG.md` entry.

A tool that reaches the network must call
`ai_service.security.host_guard.assert_host_allowed` before connecting.

## What tools must never do

- Accept raw SQL from anywhere other than the model (the model's SQL is untrusted,
  and that is exactly why validation exists).
- Return credentials, connection strings or internal identifiers.
- Perform writes of any kind, including "helpful" ones.
- Widen scope beyond `ToolContext.datasource_ids`.
- Return unbounded output (cap rows, passages and characters).
