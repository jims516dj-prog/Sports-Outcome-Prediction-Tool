#!/usr/bin/env bash
# Start the Python astrology service and the Next.js app together (Ctrl+C stops both).
# Uses .venv/bin/python when it exists; set PYTHON to use another interpreter.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
if [[ -n "${PYTHON:-}" ]]; then
  PY="$PYTHON"
elif [[ -x .venv/bin/python ]]; then
  PY=.venv/bin/python
else
  PY=python3
fi
# resolve a relative path now: the service is started from services/python-astro
if [[ "$PY" == */* && "$PY" != /* ]]; then
  PY="$ROOT/$PY"
fi
( cd services/python-astro && DATABASE_URL="${DATABASE_URL:-postgresql://astro:astro@localhost:5432/astro_football}" \
    exec "$PY" -m uvicorn main:app --host 127.0.0.1 --port 8001 ) &
SVC=$!
trap 'kill $SVC 2>/dev/null' EXIT
npx next dev -p "${PORT:-3000}"
