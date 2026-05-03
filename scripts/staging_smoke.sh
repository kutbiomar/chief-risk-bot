#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export CRB_APP_BASE="${CRB_APP_BASE:-https://app-staging.chiefriskbot.com}"
export CRB_API_BASE="${CRB_API_BASE:-https://api-staging.chiefriskbot.com/api}"
export CRB_SMOKE_REQUIRE_RESET="${CRB_SMOKE_REQUIRE_RESET:-1}"

if [[ -z "${CRB_SMOKE_EMAIL:-}" || -z "${CRB_SMOKE_PASSWORD:-}" ]]; then
  echo "CRB_SMOKE_EMAIL and CRB_SMOKE_PASSWORD are required for staging smoke." >&2
  exit 2
fi
if [[ "${CRB_SMOKE_REQUIRE_RESET}" == "1" ]]; then
  if [[ -z "${CRB_SMOKE_RESET_TOKEN:-}" || -z "${CRB_SMOKE_ROTATED_PASSWORD:-}" ]]; then
    echo "CRB_SMOKE_RESET_TOKEN and CRB_SMOKE_ROTATED_PASSWORD are required for destructive staging reset smoke." >&2
    exit 2
  fi
fi

exec scripts/prod_smoke.sh
