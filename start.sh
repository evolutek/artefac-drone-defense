#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT_DIR/.pids"

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    if [ -f "$PID_FILE" ]; then
        while read pid; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "  Killing PID $pid"
                kill "$pid" 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    echo "✅ All services stopped"
    exit 0
}

# Trap Ctrl+C and other termination signals
trap cleanup SIGINT SIGTERM

# Clear old PID file
rm -f "$PID_FILE"

echo "🚀 Starting all services..."
echo ""

# Start backend with venv
echo "Starting backend..."
(cd "$ROOT_DIR" && ./venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload) &
echo $! >> "$PID_FILE"

# Start techinal_map frontend
echo "Starting technical map..."
(cd "$ROOT_DIR/techinal_map" && npm run dev -- --port 5176) &
echo $! >> "$PID_FILE"

# Start backoffice
echo "Starting backoffice..."
(cd "$ROOT_DIR/backoffice" && python3 -m http.server 8010) &
echo $! >> "$PID_FILE"

sleep 2
echo ""
echo "✅ All services started!"
echo ""
echo "📍 URLs:"
echo "  Backend:    http://localhost:8000/"
echo "  Front Map:  http://localhost:5176/"
echo "  Backoffice: http://localhost:8010/"
echo ""
echo "💡 Press Ctrl+C to stop all services"
echo ""

# Wait for all background processes
wait