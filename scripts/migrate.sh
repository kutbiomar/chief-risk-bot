#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TIMEOUT_SECONDS="${MIGRATION_TIMEOUT_SECONDS:-180}"
ALEMBIC_BIN="${ALEMBIC_BIN:-.venv/bin/alembic}"

if [[ ! -x "$ALEMBIC_BIN" ]]; then
  echo "alembic binary not found at $ALEMBIC_BIN" >&2
  exit 1
fi

echo "Running migrations with timeout ${TIMEOUT_SECONDS}s..."
if ! timeout "$TIMEOUT_SECONDS" "$ALEMBIC_BIN" upgrade head; then
  echo "Migration command failed or timed out." >&2
  exit 2
fi

echo "Migrations applied successfully."
