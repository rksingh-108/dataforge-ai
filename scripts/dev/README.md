# `scripts/dev/`

Local quality gates. These run in CI too, so a local pass predicts a green pipeline.

| Script | Purpose | Invoked by |
| ------ | ------- | ---------- |
| `check_boundaries.py` | Enforces the service boundaries in `docs/architecture/service-boundaries.md` | `make check-boundaries`, `ci.yml` |
| `scan_secrets.sh` | Fails if a credential looks committed | `make security`, `security.yml` |
| `run-security-checks.sh` | Boundary checks + secret scan + bandit + pip-audit + Django `--deploy` | `make security` |

## `check_boundaries.py`

Three rules, each with a reason:

1. `apps/api` must not import `flask` or `ai_service` — the API and the AI service
   communicate over HTTP only.
2. `apps/ai-service` must not import `django`, `rest_framework` or `channels` — the
   AI service must never reach the platform database.
3. `apps/web` must not declare a database driver dependency — the frontend has no
   database access.

It parses Python with `ast`, so it catches dynamic imports at module level and does
not depend on grep. Migrations and `__pycache__` are skipped.

```bash
python scripts/dev/check_boundaries.py
# Service boundaries OK.
```

## `scan_secrets.sh`

Scans **tracked** files for high-signal credential patterns: AWS access keys,
OpenAI/Anthropic keys, GitHub/GitLab tokens, Slack tokens and private-key headers.
It also fails if any real `.env` file is tracked. Documentation is excluded (the
docs legitimately discuss patterns) and `.example` files are excluded (they carry
placeholders by design).

It is intentionally simple and dependency-free. It is a net, not a proof: pair it
with review discipline.

## `run-security-checks.sh`

Runs everything above plus:

- `bandit` over both Python services,
- `pip-audit` against both requirements files,
- `manage.py check --deploy` with **production** settings, using throwaway keys
  generated in the script (never real ones).

Needs both virtualenvs (`.venv` and `.venv-ai`). Use `make security`, which is
equivalent.
