# `database/seeds/`

Seed definitions for local development and reference data.

## Development seed

Implemented as a Django management command, not a SQL file, so it can use the
domain services and stay consistent with the model layer:

```bash
docker compose exec api python manage.py seed_development
```

Source: `apps/api/apps/accounts/management/commands/seed_development.py`

What it creates (idempotently):

| Account | Role |
| ------- | ---- |
| `owner@dataforge.local` | Owner |
| `admin@dataforge.local` | Admin |
| `analyst@dataforge.local` | Analyst |
| `viewer@dataforge.local` | Viewer |

All in **DataForge Demo Organization**, all with the password `DataForge!Dev1`.

It **refuses to run** unless `DEBUG=True`, so it cannot populate a non-development
environment with accounts that have a published password.

## Reference data

There is currently **no** reference-data seed. Roles and permissions are defined in
code (`apps/api/apps/common/rbac.py`), not in the database, so there is nothing to
seed. If reference data is ever needed, add a fixture here and a management command
that loads it idempotently.

## Rules

1. **Synthetic data only.** No real customer data, ever.
2. **Idempotent.** Running a seed twice must be safe.
3. **No secrets** beyond the intentionally-public development password.
4. Seeds must not be the only way a value gets created in production; production
   provisioning is a separate, documented process.
