#!/usr/bin/env bash
# Run the integration tests: the API-side tests that exercise the API <-> AI service
# boundary (with the network call to the AI service stubbed, and everything else real).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Running API boundary (integration) tests…"
exec bash "$ROOT_DIR/scripts/testing/run-backend-tests.sh" apps/ai_bridge apps/datasources "$@"
