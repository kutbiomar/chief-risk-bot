#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTEST_BIN="${PYTEST_BIN:-}"
if [[ -z "$PYTEST_BIN" ]]; then
  if [[ -x "$ROOT_DIR/.venv/bin/pytest" ]]; then
    PYTEST_BIN="$ROOT_DIR/.venv/bin/pytest"
  elif [[ -x "$ROOT_DIR/../../../.venv/bin/pytest" ]]; then
    PYTEST_BIN="$ROOT_DIR/../../../.venv/bin/pytest"
  else
    PYTEST_BIN="pytest"
  fi
fi

echo "Running backend regression suite..."
"$PYTEST_BIN" backend/tests/test_phase_cd.py backend/tests/test_auth.py backend/tests/test_security_regressions.py backend/tests/test_frontend_contract.py -q

echo "Running backend health/smoke tests..."
"$PYTEST_BIN" backend/tests/test_health.py backend/tests/test_liquidity.py -q

echo "Checking shipped frontend scripts..."
node --check frontend/_api.js
node --check frontend/_shell.js
node --check frontend/_app.js

echo "QA sweep complete."
