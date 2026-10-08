#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install Python 3.10+ and run this script again."
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created backend/.env from backend/.env.example"
fi

if ! grep -q '^SERPAPI_API_KEY=.*[^=[:space:]]' .env; then
  echo
  echo "Live hotel, flight and hotel-contact lookups need a SerpApi key."
  cd "$ROOT"
  chmod +x setup-api-key.sh
  ./setup-api-key.sh
  cd "$ROOT/backend"
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install --disable-pip-version-check -q -r requirements.txt

PORT="${PORT:-8000}"
echo "Checking backend dependencies and health on port ${PORT}..."
if ! python -c 'from app.main import app' >/dev/null 2>&1; then
  echo "Startup check failed. Re-run this script so dependencies can be repaired."
  exit 1
fi
echo "GONTOBBO is running at http://127.0.0.1:${PORT}"
echo "Live hotel and flight search is enabled when SERPAPI_API_KEY is configured."
echo "Keep this terminal open. Press Ctrl+C to stop."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
