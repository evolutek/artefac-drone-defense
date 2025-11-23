#!/bin/bash
###############################################################################
# Spawn Livraison Script - Artefac Drone Defense
# Adds a new livraison (delivery point) to the running simulation dynamically
#
# Usage:
#   bash spawn_livraison.sh <livraison_num> [x] [y] [z]
#
# Arguments:
#   livraison_num : Livraison number (0, 1, 2, 3, ...)
#   x, y, z       : Spawn position in meters (optional, defaults based on livraison_num)
#
# Examples:
#   bash spawn_livraison.sh 0          # Spawn livraison_1 at default position
#   bash spawn_livraison.sh 1 5 5 0.5  # Spawn livraison_2 at (5, 5, 0.5)
#
# What it does:
#   1. Spawns delivery point model in Gazebo at specified position (static object)
#
# Prerequisites:
#   - Gazebo simulation running
###############################################################################

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <livraison_num> [x] [y] [z]"
    echo "Example: $0 0        # Spawn livraison_1 at default position"
    echo "Example: $0 1 5 5 0.5  # Spawn livraison_2 at (5, 5, 0.5)"
    exit 1
fi

LIVR_NUM=$1
LIVR_ID="livraison_$((LIVR_NUM + 1))"  # livraison_1, livraison_2, livraison_3, ...
LIVR_NAME="livraison_${LIVR_NUM}"      # livraison_0, livraison_1, livraison_2, ...

# Position (defaults to grid pattern)
X=${2:-$((LIVR_NUM * 3))}  # 0, 3, 6, 9, ... (using bash arithmetic)
Y=${3:-0}
Z=${4:-0.5}

echo "=================================================="
echo "  Spawning Livraison ${LIVR_ID}"
echo "=================================================="
echo "Livraison Name:  $LIVR_NAME"
echo "Position:        ($X, $Y, $Z)"
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
SDF_CONTENT="<sdf version=\\\"1.9\\\"><model name=\\\"${LIVR_NAME}\\\"><pose>${X} ${Y} ${Z} 0 0 0</pose><include><uri>model://Mascot</uri></include></model></sdf>"

# Spawn via gz service (using detected world name)
gz service -s /world/${WORLD_NAME}/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --timeout 5000 \
  --req "sdf: \"${SDF_CONTENT}\""

if [ $? -eq 0 ]; then
    echo "✓ Model ${MODEL_NAME} spawned in Gazebo at ($X, $Y, $Z)"
else
    echo "✗ Failed to spawn model in Gazebo"
    exit 1
fi

