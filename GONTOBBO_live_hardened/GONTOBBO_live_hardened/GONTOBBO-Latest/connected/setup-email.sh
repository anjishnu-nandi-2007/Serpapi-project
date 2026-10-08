#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$ROOT/backend/.env"
mkdir -p "$ROOT/backend"
[ -f "$ENV_FILE" ] || cp "$ROOT/backend/.env.example" "$ENV_FILE"

read -r -p "Gmail address used to send OTPs: " EMAIL_USER
if [[ ! "$EMAIL_USER" =~ ^[^@[:space:]]+@gmail\.com$ ]]; then
  echo "Please use a valid Gmail address."
  exit 1
fi
read -r -s -p "Google App Password (not your normal Gmail password): " EMAIL_PASS
echo
if [ -z "$EMAIL_PASS" ]; then
  echo "The App Password cannot be empty."
  exit 1
fi

python3 - "$ENV_FILE" "$EMAIL_USER" "$EMAIL_PASS" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1]); user=sys.argv[2]; password=sys.argv[3]
lines=path.read_text().splitlines() if path.exists() else []
updates={
 'APP_ENV':'production','EMAIL_USER':user,'EMAIL_PASS':password,'EMAIL_FROM':user,
 'SMTP_HOST':'smtp.gmail.com','SMTP_PORT':'587','SMTP_USER':user,'SMTP_PASSWORD':password,'SMTP_FROM':user,
}
seen=set(); out=[]
for line in lines:
 key=line.split('=',1)[0].strip() if '=' in line else ''
 if key in updates:
  out.append(f'{key}={updates[key]}'); seen.add(key)
 else: out.append(line)
for key,value in updates.items():
 if key not in seen: out.append(f'{key}={value}')
path.write_text('\n'.join(out)+'\n')
PY
chmod 600 "$ENV_FILE"
echo "Gmail SMTP OTP delivery is configured in backend/.env."
echo "Restart GONTOBBO with ./start.sh and test sign-in with a real email address."
