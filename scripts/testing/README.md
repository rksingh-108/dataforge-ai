# `scripts/testing/`

Test runners. Each is responsible for provisioning whatever the suite needs, so a
developer does not have to think about infrastructure.

| Script | Runs | Needs |
| ------ | ---- | ----- |
| `run-backend-tests.sh` | `apps/api` suite (pytest) | A Postgres+pgvector database; starts a throwaway container if `TEST_DB_HOST` is unset |
| `run-ai-tests.sh` | `apps/ai-service` suite (pytest) | Nothing external |
| `run-security-tests.sh` | `apps/api/tests/security` | Same as backend |
| `run-integration-tests.sh` | API ⇄ AI-service boundary tests | Same as backend |

## `run-backend-tests.sh`

Backend tests require **real PostgreSQL with pgvector** because the schema uses
vector columns, partial unique constraints and JSONB. SQLite would hide real bugs,
so there is no SQLite path by design.

Behaviour:

1. If `TEST_DB_HOST` is set, uses that database and does not start anything.
2. Otherwise, starts `pgvector/pgvector:pg16` on port **55432** as
   `dataforge-test-db`, waits for `pg_isready`, and registers a `trap` to remove it
   on exit — including on failure or Ctrl-C.
3. Runs `pytest` in `apps/api` and passes through any extra arguments.

Override the database explicitly:

```bash
TEST_DB_HOST=localhost TEST_DB_PORT=5432 TEST_DB_USER=dataforge \
TEST_DB_PASSWORD=secret TEST_DB_NAME=dataforge_test \
  bash scripts/testing/run-backend-tests.sh
```

Or step through it manually, which is what the script does:

```bash
cd apps/api
TEST_DB_PORT=55432 ../../.venv/Scripts/python -m pytest -q          # Windows
TEST_DB_PORT=55432 ../../.venv/bin/python -m pytest -q              # macOS/Linux
```

## `run-ai-tests.sh`

Needs no external services. Provider calls are replaced by deterministic test
doubles (`ai_service/providers/testing.py`), so the suite runs in under a second.

```bash
AI_PYTHON=/path/to/.venv-ai/bin/python bash scripts/testing/run-ai-tests.sh
```

## Conventions

- `set -euo pipefail`, and `exec` the final command so its exit status is the
  script's exit status.
- Clean up with `trap`, even on failure. A leaked container blocks the next run.
- Print what is happening; CI logs are the only debugging aid there.
