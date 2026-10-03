#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Local security checks. CI runs the same commands (see .github/workflows/security.yml)
# so a failure here predicts a failure there.
# -----------------------------------------------------------------------------
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
AI_PYTHON="${AI_PYTHON:-$ROOT_DIR/.venv-ai/bin/python}"
[ -x "$PYTHON" ] || PYTHON="python"
[ -x "$AI_PYTHON" ] || AI_PYTHON="python"

EXIT=0

section() { printf '\n=== %s ===\n' "$1"; }

section "Service boundaries"
"$PYTHON" scripts/dev/check_boundaries.py || EXIT=1

section "Secret scan (tracked files)"
if bash scripts/dev/scan_secrets.sh; then
  echo "No committed secrets detected."
else
  EXIT=1
fi

# The shared config in pyproject.toml documents every skip, and the scan is
# enforcing: any non-skipped finding fails this script (and CI).
section "bandit (API)"
"$PYTHON" -m bandit -c pyproject.toml -q -r apps/api/apps || EXIT=1

section "bandit (AI service)"
"$AI_PYTHON" -m bandit -c pyproject.toml -q -r apps/ai-service/ai_service || EXIT=1

section "Dependency audit (API)"
"$PYTHON" -m pip_audit -r apps/api/requirements/base.txt --strict || EXIT=1

section "Dependency audit (AI service)"
"$AI_PYTHON" -m pip_audit -r apps/ai-service/requirements/base.txt --strict || EXIT=1

section "Django security checks"
( cd apps/api && DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_SECRET_KEY="$(printf 'x%.0s' {1..60})" \
    DATAFORGE_FERNET_KEY="$( "$PYTHON" -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
    INTERNAL_SERVICE_TOKEN="$(printf 'y%.0s' {1..40})" \
    CSRF_TRUSTED_ORIGINS="https://app.dataforge.example" \
    "$PYTHON" manage.py check --deploy ) || EXIT=1

if [ "$EXIT" -ne 0 ]; then
  echo -e "\nSecurity checks FAILED."
else
  echo -e "\nAll security checks passed."
fi
exit "$EXIT"
