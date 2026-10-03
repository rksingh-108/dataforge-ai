# Database Schema

PostgreSQL 16 with the **pgvector** extension. Migrations are owned by
`apps/api` (Django); this page is the human-readable map. If they disagree, the
migrations win.

## Tables

### `accounts_user`
UUID pk · `email` (unique, indexed) · `full_name` · `is_active` · `is_staff` ·
`is_superuser` · `date_joined` · `last_login` · password hash.
Index: `(is_active)`. Login is by email.

### `organizations_organization`
UUID pk · `name` · `slug` (unique) · `is_active` · `created_by` → user · timestamps.
Constraint: `organization_name_not_blank`.

### `organizations_membership`
UUID pk · `organization` → organization · `user` → user · `role` · `is_active` ·
timestamps.
Constraint: `unique_membership_per_org` on `(organization, user)`.
Index: `(user, is_active)`.
The unit of authorization. `role` ∈ `{owner, admin, analyst, viewer}`.

### `datasources_datasource`
UUID pk · `organization` → organization · `name` · `description` · `engine`
(`postgresql`|`mysql`) · `host` · `port` · `database_name` · `username` ·
`password_encrypted` (**bytea, Fernet**) · `is_read_only` (default true) ·
`ssl_mode` · `status` (`unknown`|`connected`|`error`) · `last_error` ·
`last_tested_at` · `last_synced_at` · `created_by` · timestamps.
Constraints: `unique_datasource_name_per_org`. Index: `(organization, status)`.

### `datasources_schematable` / `datasources_schemacolumn`
Cached schema discovery, used to build the SQL allowlist.
`unique_table_per_datasource` on `(datasource, schema_name, table_name)`;
`unique_column_per_table` on `(table, column_name)`.
Replaced atomically on each sync.

### `documents_document`
UUID pk · `organization` · `title` · `original_filename` · `content_type` ·
`size_bytes` · `checksum_sha256` · `file` · `status`
(`pending`|`processing`|`ready`|`failed`) · `error` · `page_count` · `chunk_count` ·
`processed_at` · `uploaded_by` · timestamps.
Constraints: `unique_document_checksum_per_org` on `(organization, checksum)`,
**partial** (only when the checksum is non-empty).
Indexes: `(organization, -created_at)`, `(organization, status)`.

### `documents_documentchunk`
UUID pk · `document` → document · `organization` (**denormalized**) ·
`chunk_index` · `content` · `char_count` · `source_label` · `embedding`
`vector(1536)` · `metadata` (JSONB).
Constraints: `unique_chunk_index_per_document` on `(document, chunk_index)`.
Indexes: `(organization)`, plus **HNSW** `document_chunk_embedding_hnsw`
(`vector_cosine_ops`, m=16, ef_construction=64).

> The denormalized `organization` lets vector search filter by tenant without a
> join — a deliberate trade of a little redundancy for a safer, faster hot path.

### `analytics_execution`
UUID pk · `organization` · `kind` (`analyst_query`|`document_processing`) ·
`status` (`pending`|`running`|`succeeded`|`failed`) · `question` · `answer` ·
`error` · `user` · `datasource` (nullable) · `document` (nullable) · `provider` ·
`model_name` · `total_tokens` · `duration_ms` · `started_at` · `finished_at` ·
`request_id` · timestamps.
Indexes: `(organization, -created_at)`, `(organization, status)`, `(kind)`.

### `analytics_executionstep`
UUID pk · `execution` → execution · `index` · `tool_name` · `title` · `status` ·
`input_summary` (JSONB) · `output_summary` (JSONB) · `duration_ms` · `error`.
Constraint: `unique_step_index` on `(execution, index)`.
Stores tool-level summaries only — **never private model reasoning**.

### `analytics_auditlog`
UUID pk · `organization` (**nullable**: account-level events) · `actor` (nullable) ·
`action` · `target_type` · `target_id` · `metadata` (JSONB) · `ip_address` ·
`request_id` · `created_at`.
Indexes: `(organization, -created_at)`, `(action)`, `(actor)`.
**Append-only**: the model raises on update and delete.

### Django/third-party
`django.contrib.sessions`, `admin`, `contenttypes`, `auth` (permissions only —
we use our own user model), `rest_framework_simplejwt.token_blacklist`
(`outstandingtoken`, `blacklistedtoken`), `django_celery_beat`.

## Extension setup

`apps/api/apps/documents/migrations/0000_enable_pgvector.py` runs
`CREATE EXTENSION IF NOT EXISTS vector` and the document migration depends on it,
so the extension always exists before any vector column or HNSW index.

## Retention

**Not implemented.** Executions and audit logs are retained indefinitely. See
known limitation D2.

## Migration policy

- Reviewed by the Data owner (CODEOWNERS).
- Reversible, or the PR explains why not.
- Constraints encode invariants rather than leaving them to application code.
- Indexes are added with the query that needs them.
- Data migrations are idempotent and have a documented rollback.

## Useful queries

```sql
-- Table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC;

-- Chunk counts per organization
SELECT organization_id, COUNT(*) FROM documents_documentchunk GROUP BY 1;

-- Index usage for the vector index
SELECT indexrelname, idx_scan FROM pg_stat_user_indexes
WHERE indexrelname = 'document_chunk_embedding_hnsw';

-- Audit activity by action
SELECT action, COUNT(*) FROM analytics_auditlog GROUP BY 1 ORDER BY 2 DESC;
```
