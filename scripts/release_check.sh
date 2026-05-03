#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
PYTEST_BIN="${PYTEST_BIN:-.venv/bin/pytest}"
ALEMBIC_BIN="${ALEMBIC_BIN:-.venv/bin/alembic}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi
if [[ ! -x "$PYTEST_BIN" ]]; then
  PYTEST_BIN="pytest"
fi
if [[ ! -x "$ALEMBIC_BIN" ]]; then
  ALEMBIC_BIN="alembic"
fi

section() {
  printf "\n== %s ==\n" "$1"
}

section "Whitespace diff check"
git diff --check

section "Python syntax"
python_files=()
while IFS= read -r path; do
  python_files+=("$path")
done < <({
  git diff --name-only --diff-filter=ACMRT HEAD -- '*.py'
  find backend admin scripts -name '*.py' -type f
} | sort -u)
if (( ${#python_files[@]} )); then
  "$PYTHON_BIN" -m py_compile "${python_files[@]}"
fi

section "JavaScript syntax"
node --check frontend-mvp/_app.js
node --check frontend-mvp/_shell.js

section "Shell syntax"
bash -n scripts/release_check.sh scripts/staging_smoke.sh scripts/prod_smoke.sh scripts/observability_smoke.sh

section "Backend tests"
"$PYTEST_BIN" backend/tests -q

section "Destructive migration check"
python3 scripts/check_destructive_migrations.py

section "Alembic disposable upgrade"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
DATABASE_URL="sqlite:///$tmp_dir/release_check.db" \
AUTH_MODE=local \
SECRET_KEY=release-check-local-secret \
"$ALEMBIC_BIN" upgrade head

section "Staging smoke"
if [[ "${CRB_SKIP_STAGING_SMOKE:-}" == "1" ]]; then
  echo "Skipping staging smoke because CRB_SKIP_STAGING_SMOKE=1."
else
  scripts/staging_smoke.sh
fi

section "Observability smoke"
if [[ "${CRB_SKIP_OBSERVABILITY_SMOKE:-}" == "1" ]]; then
  echo "Skipping observability smoke because CRB_SKIP_OBSERVABILITY_SMOKE=1."
else
  scripts/observability_smoke.sh
fi

section "Release check complete"
