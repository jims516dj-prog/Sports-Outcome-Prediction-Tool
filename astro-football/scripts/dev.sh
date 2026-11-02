#!/usr/bin/env bash
# Start the Python astrology service and the Next.js app together (Ctrl+C stops both).
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
( cd services/python-astro && DATABASE_URL="${DATABASE_URL:-postgresql://astro:astro@localhost:5432/astro_football}" \
    "$PY" -m uvicorn main:app --host 127.0.0.1 --port 8001 ) &
SVC=$!
trap 'kill $SVC 2>/dev/null' EXIT
npx next dev -p "${PORT:-3000}"
