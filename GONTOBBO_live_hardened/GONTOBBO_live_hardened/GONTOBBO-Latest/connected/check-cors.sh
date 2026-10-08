#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8000}"
BASE="http://127.0.0.1:${PORT}"
echo "Checking GONTOBBO backend at ${BASE}"
curl -fsS "${BASE}/api/health"; echo
printf 'CORS preflight: '
curl -fsS -o /dev/null -w '%{http_code}\n' -X OPTIONS "${BASE}/api/send-otp" \
  -H 'Origin: http://127.0.0.1:5500' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type'
echo "CORS check passed."
