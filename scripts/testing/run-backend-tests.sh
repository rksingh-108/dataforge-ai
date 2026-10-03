#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Run the Django test suite against a real PostgreSQL + pgvector database.
#
# If TEST_DATABASE_URL / TEST_DB_* are already set, that database is used.
# Otherwise a throwaway container is started and torn down automatically.
# -----------------------------------------------------------------------------
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON="python"

CONTAINER="dataforge-test-db"
STARTED_CONTAINER=0

start_db() {
  if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "Reusing running container $CONTAINER"
    return
  fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  echo "Starting throwaway Postgres (pgvector) on port 55432…"
  docker run -d --name "$CONTAINER" \
    -e POSTGRES_USER=dataforge \
    -e POSTGRES_PASSWORD=dataforge \
    -e POSTGRES_DB=dataforge_test \
    -p 55432:5432 \
    pgvector/pgvector:pg16 >/dev/null
  STARTED_CONTAINER=1
  for _ in $(seq 1 40); do
    if docker exec "$CONTAINER" pg_isready -U dataforge >/dev/null 2>&1; then break; fi
    sleep 1
  done
}

cleanup() {
  if [ "$STARTED_CONTAINER" = "1" ]; then
    echo "Stopping throwaway database…"
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  fi
}

if [ -z "${TEST_DB_HOST:-}" ]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is required (or set TEST_DB_HOST/TEST_DB_PORT to a Postgres+pgvector instance)." >&2
    exit 1
  fi
  trap cleanup EXIT
  start_db
  export TEST_DB_HOST=localhost
  export TEST_DB_PORT=55432
  export TEST_DB_USER=dataforge
  export TEST_DB_PASSWORD=dataforge
  export TEST_DB_NAME=dataforge_test
fi

cd "$API_DIR"
exec "$PYTHON" -m pytest "$@"
