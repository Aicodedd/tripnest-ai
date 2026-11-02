#!/bin/sh
# Browser end-to-end tests against an isolated server (throwaway SQLite database, saved crowd model).
# Needs Google Chrome and Playwright (pip install -r requirements-dev.txt).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
export DATABASE_URL="sqlite:///$TMP/e2e.db" ENV=test PHOTO_PROVIDER="${PHOTO_PROVIDER:-off}" \
  SECRET_KEY="e2e-secret-key-not-for-production-1234567890"
cd "$ROOT"
HELPER="${WITH_SERVER:-$HOME/.claude/skills/webapp-testing/scripts/with_server.py}"
if [ -f "$HELPER" ]; then
  .venv/bin/python "$HELPER" --server "cd backend && exec ../.venv/bin/uvicorn app.main:app --port 8020" --port 8020 --timeout 60 \
    -- .venv/bin/python -m pytest e2e -v "$@"
else
  (cd backend && exec ../.venv/bin/uvicorn app.main:app --port 8020 >/dev/null 2>&1 &)
  for i in $(seq 1 60); do curl -sf localhost:8020/api/health >/dev/null && break; sleep 1; done
  status=0
  .venv/bin/python -m pytest e2e -v "$@" || status=$?
  pkill -f "uvicorn app.main:app --port 8020" || true
  exit $status
fi
