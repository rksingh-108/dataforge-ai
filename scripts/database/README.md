# `scripts/database/`

Migration, seed and maintenance helpers owned by the **Data/Database** team. See
[`database/README.md`](../../database/README.md) for the schema overview and
[`docs/database/schema.md`](../../docs/database/schema.md) for the model reference.

## Status

The everyday database commands are already covered by the Makefile and do not
need a script:

```bash
make migrate        # docker compose exec api python manage.py migrate --noinput
make makemigrations # create a new migration
make seed           # python manage.py seed_development (DEBUG only)
make db-shell       # psql into the platform database
```

Nothing else is automated yet, so no script is shipped. A script that wrapped a
single `manage.py` call would be indirection without value.

## What belongs here

Helpers that are genuinely non-trivial and worth testing:

| Helper | Responsibility |
| ------ | -------------- |
| `load_fixtures.py` | Load a named fixture set into a target environment; referenced by [`database/fixtures/README.md`](../../database/fixtures/README.md) |
| `check_migrations.sh` | Fail if `makemigrations --check` reports drift (models changed without a migration) |
| `backup.sh` / `restore.sh` | `pg_dump`/`pg_restore` wrappers once backups exist (known limitation **D1**) |
| `partition_audit_logs.py` | Introduce partitioning for `audit_logs` once volume requires it (known limitation **D3**) |

## Conventions

Follow [`../README.md`](../README.md). Two rules specific to this directory:

1. **Read-only by default.** A maintenance script must not mutate platform data
   unless its name says so and it takes an explicit confirmation flag.
2. **Never point at production implicitly.** Require the target to be passed in;
   do not default to a host from `.env`.
