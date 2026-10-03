#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Fail if anything that looks like a committed credential is tracked by git.
#
# Deliberately simple and dependency-free: a curated set of high-signal patterns
# plus an explicit allowlist for documentation placeholders.
# -----------------------------------------------------------------------------
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git repository; skipping secret scan." >&2
  exit 0
fi

PATTERNS=(
  'AKIA[0-9A-Z]{16}'                                  # AWS access key id
  'sk-[A-Za-z0-9]{20,}'                               # OpenAI-style key
  'sk-ant-[A-Za-z0-9_-]{20,}'                         # Anthropic key
  'ghp_[A-Za-z0-9]{30,}'                              # GitHub PAT
  'glpat-[A-Za-z0-9_-]{20,}'                          # GitLab PAT
  '-----BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY-----'  # private keys
  'xox[baprs]-[A-Za-z0-9-]{10,}'                      # Slack token
)

# Files and patterns that are intentionally allowed.
EXCLUDE_PATHS=(
  ':!*.example'
  ':!.env.example'
  ':!docs/**'
  ':!security/**'
  ':!scripts/dev/scan_secrets.sh'
  ':!**/*.md'
)

FOUND=0
for pattern in "${PATTERNS[@]}"; do
  matches="$(git grep -nIE "$pattern" -- . "${EXCLUDE_PATHS[@]}" 2>/dev/null || true)"
  if [ -n "$matches" ]; then
    echo "Potential secret matching /$pattern/:"
    echo "$matches"
    FOUND=1
  fi
done

# Hard failure: a real (non-example) env file must never be tracked.
TRACKED_ENV="$(git ls-files | grep -E '(^|/)\.env$|(^|/)\.env\.[^e]' || true)"
if [ -n "$TRACKED_ENV" ]; then
  echo "Tracked environment files (must never be committed):"
  echo "$TRACKED_ENV"
  FOUND=1
fi

exit "$FOUND"
