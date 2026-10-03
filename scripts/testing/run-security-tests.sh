#!/usr/bin/env bash
# Run the cross-cutting security test suite: tenant isolation and tenant-scope
# resolution, the authorization matrix, headers, throttling, plus the WebSocket
# authorization tests (which live with the realtime app). Needs PostgreSQL +
# pgvector, like the rest of the backend suite.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Running the API security suite…"
exec bash "$ROOT_DIR/scripts/testing/run-backend-tests.sh" tests/security apps/realtime/tests "$@"
