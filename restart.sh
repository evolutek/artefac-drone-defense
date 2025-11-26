#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🔄 Restarting all services..."
echo ""

# Stop existing services
"$ROOT_DIR/stop.sh"

echo ""
echo "⏳ Waiting 2 seconds..."
sleep 2
echo ""

# Start services
exec "$ROOT_DIR/start.sh"
