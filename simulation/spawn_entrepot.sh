#!/bin/bash
###############################################################################
# Spawn Entrepôt Script - Artefac Drone Defense
# Adds a new entrepôt (warehouse) to the running simulation dynamically
#
# Usage:
#   bash spawn_entrepot.sh <entrepot_num> [x] [y] [z]
#
# Arguments:
#   entrepot_num : Entrepôt number (0, 1, 2, 3, ...)
#   x, y, z      : Spawn position in meters (optional, defaults based on entrepot_num)
#
# Examples:
#   bash spawn_entrepot.sh 0          # Spawn entrepot_1 at default position
#   bash spawn_entrepot.sh 1 5 5 0.5  # Spawn entrepot_2 at (5, 5, 0.5)
#
# What it does:
#   1. Spawns shelf model in Gazebo at specified position (static object)
#
# Prerequisites:
#   - Gazebo simulation running
###############################################################################

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <entrepot_num> [x] [y] [z]"
    echo "Example: $0 0        # Spawn entrepot_1 at default position"
    echo "Example: $0 1 5 5 0.5  # Spawn entrepot_2 at (5, 5, 0.5)"
    exit 1
fi

ENTR_NUM=$1
ENTR_ID="entrepot_$((ENTR_NUM + 1))"  # entrepot_1, entrepot_2, entrepot_3, ...
ENTR_NAME="entrepot_$2"      # entrepot_0, entrepot_1, entrepot_2, ...

# Position (defaults to grid pattern)
X=${3:-$((ENTR_NUM * 3))}  # 0, 3, 6, 9, ... (using bash arithmetic)
Y=${4:-0}
Z=${5:-0.5}

echo "=================================================="
echo "  Spawning Entrepôt ${ENTR_ID}"
echo "=================================================="
echo "Entrepôt Name:  $ENTR_NAME"
echo "Position:       ($X, $Y, $Z)"
echo "=================================================="

# Step 1: Spawn model in Gazebo
echo ""
echo "[1/1] Spawning model in Gazebo..."

# Check if Gazebo server is accessible (works across containers with network_mode: host)
if ! timeout 5 gz service --list > /dev/null 2>&1; then
    echo "ERROR: Gazebo simulation is not accessible!"
    echo "  (Gazebo server might be running in a different container)"
    exit 1
fi

# Detect world name dynamically
WORLD_NAME=$(gz service --list | grep -oP '/world/\K[^/]+' | head -1)
if [ -z "$WORLD_NAME" ]; then
    echo "ERROR: Could not detect Gazebo world name"
    exit 1
fi
echo "Detected Gazebo world: $WORLD_NAME"

# Construct SDF without XML declaration (Gazebo doesn't need it and it causes protobuf parsing issues)
# Use escaped double quotes for proper protobuf text format parsing
SDF_CONTENT="<sdf version=\\\"1.9\\\"><model name=\\\"${ENTR_NAME}\\\"><pose>${X} ${Y} ${Z} 0 0 0</pose><static>true</static><include><uri>model://shelf/</uri></include></model></sdf>"

# Spawn via gz service (using detected world name)
gz service -s /world/${WORLD_NAME}/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --timeout 5000 \
  --req "sdf: \"${SDF_CONTENT}\""

if [ $? -eq 0 ]; then
    echo "✓ Model ${ENTR_NAME} spawned in Gazebo at ($X, $Y, $Z)"
else
    echo "✗ Failed to spawn model in Gazebo"
    exit 1
fi

