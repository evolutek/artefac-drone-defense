#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

(cd "$ROOT_DIR" && python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload) &

(cd "$ROOT_DIR/techinal_map" && npm run dev -- --port 5176) &

(cd "$ROOT_DIR/backoffice" && python3 -m http.server 8010) &

sleep 1
echo "Backend:   http://localhost:8001/"
echo "Front Map: http://localhost:5176/"
echo "Backoffice: http://localhost:8010/"
