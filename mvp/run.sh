#!/usr/bin/env bash
# Boot the RiskPilot MVP. Creates a venv on first run.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creating venv..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [ ! -f .venv/.deps-installed ]; then
  echo "Installing dependencies..."
  pip install --upgrade pip >/dev/null
  pip install -r requirements.txt
  touch .venv/.deps-installed
fi

if [ ! -f .env ]; then
  echo "No .env file found. Copy .env.example to .env and fill in your ANTHROPIC_API_KEY."
  exit 1
fi

echo ""
echo "RiskPilot MVP running at http://127.0.0.1:8000"
echo "Upload sample_portfolio.csv to try it immediately."
echo ""

exec uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
