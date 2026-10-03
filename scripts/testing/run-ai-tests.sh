#!/usr/bin/env bash
# Run the AI service test suite. No external services are required.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AI_DIR="$ROOT_DIR/apps/ai-service"
PYTHON="${AI_PYTHON:-$ROOT_DIR/.venv-ai/bin/python}"
[ -x "$PYTHON" ] || PYTHON="python"

cd "$AI_DIR"
exec "$PYTHON" -m pytest "$@"
