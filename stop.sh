#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT_DIR/.pids"

echo "🛑 Stopping all services..."

# Function to kill by port
kill_by_port() {
    echo "  Killing processes on ports 8000, 8010, 5176..."
    lsof -ti:8000,8010,5176 2>/dev/null | xargs -r kill 2>/dev/null || true
    sleep 1
    lsof -ti:8000,8010,5176 2>/dev/null | xargs -r kill -9 2>/dev/null || true
}

# Stop using PID file if it exists
if [ -f "$PID_FILE" ]; then
    while read pid; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Stopping PID $pid..."
            kill "$pid" 2>/dev/null || true
        fi
    done < "$PID_FILE"

    # Wait a bit and force kill if needed
    sleep 1
    while read pid; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Force killing PID $pid..."
            kill -9 "$pid" 2>/dev/null || true
        fi
    done < "$PID_FILE"

    rm -f "$PID_FILE"
fi

# Also kill by port as a safety measure
kill_by_port

# Kill any remaining node/python processes for these services
pkill -f "vite --port 5176" 2>/dev/null || true
pkill -f "uvicorn backend.app.main" 2>/dev/null || true
pkill -f "http.server 8010" 2>/dev/null || true

echo "✅ All services stopped"
