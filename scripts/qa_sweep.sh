#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Running backend regression suite..."
.venv/bin/pytest backend/tests/test_phase_cd.py backend/tests/test_auth.py backend/tests/test_security_regressions.py -q

echo "Running backend health/smoke tests..."
.venv/bin/pytest backend/tests/test_health.py backend/tests/test_liquidity.py -q

echo "Checking shipped frontend scripts..."
node --check frontend-mvp/_app.js
node --check frontend-mvp/_shell.js

echo "QA sweep complete."
