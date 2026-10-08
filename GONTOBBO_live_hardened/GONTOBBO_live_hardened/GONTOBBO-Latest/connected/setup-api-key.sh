#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$ROOT/backend/.env"
mkdir -p "$ROOT/backend"
[ -f "$ENV_FILE" ] || cp "$ROOT/backend/.env.example" "$ENV_FILE"
read -r -s -p "SerpApi API key (input hidden): " SERPAPI_API_KEY
echo
if [ -z "${SERPAPI_API_KEY//[[:space:]]/}" ]; then
  echo "The SerpApi key cannot be empty."
  exit 1
fi
python3 - "$ENV_FILE" "$SERPAPI_API_KEY" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
key = sys.argv[2].strip()
lines = path.read_text().splitlines() if path.exists() else []
out = []
seen = False
for line in lines:
    if line.startswith('SERPAPI_API_KEY='):
        if not seen:
            out.append('SERPAPI_API_KEY=' + key)
            seen = True
    else:
        out.append(line)
if not seen:
    out.insert(0, 'SERPAPI_API_KEY=' + key)
path.write_text('\n'.join(out) + '\n')
PY
chmod 600 "$ENV_FILE"
echo "SerpApi is configured in backend/.env. Start GONTOBBO with ./start.sh."
