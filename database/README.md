# `database/`

Material owned by the **Data** team. Django migrations live with the apps they
belong to (`apps/api/apps/*/migrations/`), because that is where Django requires
them. This directory holds everything that is *not* a migration.

| Path | Contents |
| ---- | -------- |
| `migrations/` | SQL that must run before or outside Django migrations (extension checks, helper functions). Most schema changes belong in Django migrations instead. |
| `seeds/` | Reference data and development seed definitions |
| `fixtures/` | Fixture data for local development and tests. **Synthetic only.** |
| `docs/` | Database-specific documentation |

## Where does my change go?

| Change | Location |
| ------ | -------- |
| New table, column, index or constraint | Django migration in the owning app |
| Enabling an extension | `apps/api/apps/documents/migrations/0000_enable_pgvector.py` (the pattern to copy) |
| Reference/lookup data | `database/seeds/` + a management command |
| Test fixture | `database/fixtures/` |
| Schema explanation | `docs/database/schema.md` |

## Rules

1. **No real customer data** in this directory, ever. Not in fixtures, seeds or
   examples. Use synthetic values.
2. **Migrations are reviewed by the Data owner** through `CODEOWNERS`.
3. **Every migration is reversible**, or the PR explains why not and how to recover.
4. **No secrets.** Connection strings, passwords and keys never appear here.
5. Fixtures must be loadable idempotently.

## Applying

```bash
make migrate        # Django migrations
make seed           # development organization and users
```

Django owns the schema. Do not apply manual DDL to a live database; create a
migration.

## See also

- [docs/database/schema.md](../docs/database/schema.md) — the human-readable schema
- [docs/onboarding/database-developer.md](../docs/onboarding/database-developer.md) — the working guide
- [docs/architecture/data-flow.md](../docs/architecture/data-flow.md) — how data moves
