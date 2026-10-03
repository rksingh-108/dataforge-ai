# Data Flow

Four flows carry essentially all the data in the system.

## 1. Authentication

```
Browser ──POST /api/auth/login──▶ Next BFF ──POST /api/v1/auth/login/──▶ API
                                     │                                     │
                       httpOnly cookies ◀── {access, refresh} ───────────┘
```

1. The BFF forwards credentials to the API.
2. The API authenticates, issues a short-lived access token and a rotating
   refresh token, and records `auth.login` in the audit log.
3. The BFF stores both in **httpOnly** cookies and returns only the user profile.
4. Subsequent browser calls go to `/api/proxy/...`; the BFF attaches the access
   token and refreshes once on a 401.

The access token is never exposed to JavaScript. See
[authentication-flow.md](authentication-flow.md).

## 2. AI analyst query

```
Browser ─POST /api/v1/orgs/{id}/analyst/query/─▶ Next BFF ─▶ API
                                                             │ 1. authorize (membership + analyst.query)
                                                             │ 2. create Execution (status=running)
                                                             │ 3. filter datasource ids to owned ones
                                                             ▼
                                                     AI service  /v1/agent/run
                                                             │
                                        ┌────────────────────┴────────────────────┐
                                        │ agent loop (bounded iterations)         │
                                        │  model ─▶ tool call ─▶ validate ─▶ run  │
                                        └────────────────────┬────────────────────┘
                                                             │
                          ┌──────────────────────────────────┼──────────────────────────────┐
                          ▼                                  ▼                              ▼
             GET /internal/datasources/{id}/schema   GET .../connection         POST /internal/documents/search
             (cached table list; SQL allowlist)      (decrypted config,          (pgvector cosine search,
                                                     audit-logged)               org-filtered)
                                                             │
                                              Postgres/MySQL (read-only session)
                                                             │
                                        ◀────────────────────┘ {answer, steps, tokens}
                                                             │
                                     4. persist ExecutionStep rows, finish Execution
                                     5. broadcast on the org WebSocket group
```

Key points:

- The API decides **what the AI service may touch** before any AI work happens.
- The AI service never opens the platform database.
- SQL is validated against the allowlist derived from the schema the API returned.
- Every credential retrieval is audit-logged.
- The model never sees a credential.

## 3. Document ingestion (RAG)

```
Browser ─multipart──▶ BFF ─▶ API
                            │ 1. validate (extension, type, magic bytes, size, checksum)
                            │ 2. store file under documents/<org>/<uuid>.<ext>
                            │ 3. create Document (status=processing)
                            │ 4. enqueue Celery task
                            ▼
                       Redis (broker)
                            │
                            ▼
                    Celery worker (API image)
                            │ 5. read file, base64 it
                            │ 6. POST /v1/rag/process ─────▶ AI service
                            │                                   │ extract (pypdf/docx/txt)
                            │                                   │ chunk (paragraph-aware, overlapping)
                            │                                   │ embed (configured provider)
                            │ 7. persist DocumentChunk rows ◀───┘ {chunks + embeddings}
                            │ 8. Document.status = ready
                            ▼
                    PostgreSQL + pgvector (HNSW index)
```

The worker writes the chunks because the API is the only writer to the platform
database. Retrieval later happens through the API's internal search endpoint.

## 4. Execution and audit records

```
any action ─▶ API service layer ─┬─▶ Execution / ExecutionStep   (what the AI did)
                                 ├─▶ AuditLog (append-only)      (who did what, from where)
                                 └─▶ WebSocket broadcast         (live status)
```

- `Execution` is mutable (status transitions); `AuditLog` is append-only by
  construction — `save()` on an existing row and `delete()` raise.
- Every record carries `organization_id`, so history is tenant-scoped like
  everything else.
- `request_id` propagates from the browser through the API to the AI service, so a
  user-visible error can be traced across all three tiers.

## What never flows

| Never | Why |
| ----- | --- |
| Data-source passwords → browser | Serializers expose no credential fields |
| Data-source passwords → LLM prompt | Tools fetch them; only redacted summaries enter the trace |
| Access tokens → JavaScript | httpOnly cookies only |
| Platform database ← AI service | The AI service has no platform DB credentials |
| One organization's data → another | Every query is org-scoped; 404 on cross-tenant access |
