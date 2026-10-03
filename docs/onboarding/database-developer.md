# Onboarding — Data / Database Developer

## Your area

**You own:** the platform schema, migrations, seeds, fixtures and database
documentation. You co-own `database/` with backend, and you review every migration
through `CODEOWNERS` (`apps/api/apps/*/migrations/`).

## Where the schema lives

Migrations are Django migrations, inside each app:

```
apps/api/apps/accounts/migrations/
apps/api/apps/organizations/migrations/
apps/api/apps/datasources/migrations/
apps/api/apps/documents/migrations/          # includes the pgvector extension
apps/api/apps/analytics/migrations/
```

The top-level `database/` directory holds material that is **not** a Django
migration: the seed/fixture definitions, SQL that has to run before migrations,
and the schema documentation. See [database/README.md](../../database/README.md).

## Set up

```bash
docker compose up -d db
cd apps/api
python manage.py migrate
python manage.py seed_development
```

Connect:

```bash
docker compose exec db psql -U dataforge -d dataforge
```

## The schema in one page

| Table | Purpose | Tenancy |
| ----- | ------- | ------- |
| `accounts_user` | Users (email login, UUID pk) | global |
| `organizations_organization` | Tenant boundary | — |
| `organizations_membership` | User × organization × role | belongs to organization |
| `datasources_datasource` | Connection records; password is `bytea`, Fernet-encrypted | organization |
| `datasources_schematable` / `_schemacolumn` | Cached discovered schema (the SQL allowlist) | via datasource |
| `documents_document` | Uploaded files and processing status | organization |
| `documents_documentchunk` | Text chunks with a `vector(1536)` embedding | organization (denormalized) |
| `analytics_execution` / `_executionstep` | AI runs and their tool calls | organization |
| `analytics_auditlog` | Append-only security events | nullable (account events) |

### Conventions

1. UUID primary keys everywhere (`UUIDModel`) — safe to expose, no enumeration.
2. `created_at` / `updated_at` on every model (`TimeStampedModel`).
3. Tenant-owned models inherit `OrganizationScopedModel`, so `organization_id` is
   structurally guaranteed to exist.
4. Constraints express real invariants: `unique_membership_per_org`,
   `unique_datasource_name_per_org`, `unique_chunk_index_per_document`,
   `unique_document_checksum_per_org` (partial: only when the checksum is set).
5. Indexes follow the queries. Every organization-scoped table has an index leading
   with `organization_id`; executions and audit logs additionally index
   `(organization, -created_at)`.
6. `DocumentChunk.embedding` has an **HNSW** index with `vector_cosine_ops`.

## pgvector

The extension is created by `apps/api/apps/documents/migrations/0000_enable_pgvector.py`,
which the document migration depends on. This must run before any vector column or
index exists.

The embedding dimension is **fixed at migration time**
(`EMBEDDING_DIM`, default 1536). Changing it requires a new migration and
re-embedding every chunk — see [known-limitations.md](../development/known-limitations.md) (I5).

## Adding a migration

```bash
cd apps/api
python manage.py makemigrations <app>
python manage.py sqlmigrate <app> <number>    # review the SQL
python manage.py migrate
```

Review checklist:

- [ ] Is the migration reversible? If not, say so in the PR and in `docs/database/schema.md`.
- [ ] Are there indexes for the queries this enables?
- [ ] Do constraints encode the invariant, rather than relying on application code?
- [ ] For a data migration: is there a rollback plan and is it idempotent?
- [ ] Does `apps/api/tests/` still pass (migrations run in tests)?

## Testing

```bash
make test-backend
```

Backend tests run against **real PostgreSQL + pgvector**, so migrations, vector
search and constraints are genuinely exercised. There is no SQLite path by design.

Vector-specific tests live in `apps/api/apps/documents/tests/test_vector_search.py`
and are marked `requires_postgres`.

## Good first tasks

- Add a missing index with a migration and a one-line justification.
- Add a constraint that encodes an invariant currently enforced only in Python.
- Write a data migration with a `reverse_code` and test it.
- Improve `docs/database/schema.md`.

## Ask about

- Anything that changes a tenant column or a unique constraint → backend + security.
- Any change to the embedding dimension → AI owner first; it is a coordinated change.
