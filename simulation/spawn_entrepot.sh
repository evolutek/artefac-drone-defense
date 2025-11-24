#!/bin/bash
###############################################################################
# Spawn Warehouse (Entrepôt) Script - Artefac Drone Defense
# Creates a 3D warehouse model in Gazebo simulation
#
# Usage:
#   bash spawn_entrepot.sh <entrepot_num> <name> [x] [y] [z]
#
# Arguments:
#   entrepot_num : Warehouse number (0, 1, 2, ...) - used for internal tracking
#   name         : Human-readable warehouse name (e.g., "Main Warehouse")
#   x, y, z      : Position in meters (optional, defaults to grid pattern)
#
# Examples:
#   bash spawn_entrepot.sh 0 "Warehouse Alpha"
#   bash spawn_entrepot.sh 1 "Medical Depot" 5 5 0.5
#
# What it does:
#   1. Normalizes warehouse name to create Gazebo model name (entrepot_<normalized_name>)
#   2. Spawns 3D shelf model at specified position
#   3. Uses Gazebo's built-in "shelf" model
#
# Prerequisites:
#   - Gazebo simulation running
#   - gz command available
###############################################################################

set -e

# ============================================================================
# Argument Parsing
# ============================================================================

if [ $# -lt 2 ]; then
    echo "Usage: $0 <entrepot_num> <name> [x] [y] [z]"
    echo "Example: $0 0 'Warehouse Alpha'        # Default position"
    echo "Example: $0 1 'Medical Depot' 5 5 0.5  # Custom position"
    exit 1
fi

ENTREPOT_NUM=$1
USER_ENTREPOT_NAME=${2:-"unnamed_${ENTREPOT_NUM}"}

# Position (with defaults)
X=${3:-$((ENTREPOT_NUM * 20))}  # Grid pattern: 0, 20, 40, ...
Y=${4:-0}
Z=${5:-0}

# ============================================================================
# Name Normalization
# ============================================================================

# Normalize warehouse name for Gazebo model (lowercase, spaces→underscores, alphanumeric only)
NORMALIZED_NAME=$(echo "$USER_ENTREPOT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd '[:alnum:]_')

# Gazebo model name with entrepot_ prefix for easy discovery
ENTREPOT_MODEL_NAME="entrepot_${NORMALIZED_NAME}"

# ============================================================================
# Status Output
# ============================================================================

echo "=================================================="
echo "  Spawning Warehouse (Entrepôt)"
echo "=================================================="
echo "User Name:   $USER_ENTREPOT_NAME"
echo "Model Name:  $ENTREPOT_MODEL_NAME"
echo "Position:    ($X, $Y, $Z)"
echo "=================================================="

# ============================================================================
# Gazebo Connection Check
# ============================================================================

echo -e "\n[1/1] Spawning model in Gazebo..."

if ! timeout 5 gz service --list > /dev/null 2>&1; then
    echo "ERROR: Gazebo simulation is not accessible!"
    echo "  (Make sure Gazebo is running in the simulation container)"
    exit 1
fi

# Detect world name dynamically
WORLD_NAME=$(gz service --list | grep -oP '/world/\K[^/]+' | head -1)
if [ -z "$WORLD_NAME" ]; then
    echo "ERROR: Could not detect Gazebo world name"
    exit 1
fi
echo "Detected Gazebo world: $WORLD_NAME"

# ============================================================================
# SDF Generation & Spawn
# ============================================================================

# Construct SDF as single-line string (uses built-in shelf model)
SDF_CONTENT="<sdf version=\\\"1.9\\\"><model name=\\\"$ENTREPOT_MODEL_NAME\\\"><pose>${X} ${Y} ${Z} 0 0 0</pose><include><uri>model://shelf</uri></include></model></sdf>"

# Spawn via gz service
gz service -s /world/$WORLD_NAME/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --req "sdf: \"${SDF_CONTENT}\", name: \"${ENTREPOT_MODEL_NAME}\""

if [ $? -eq 0 ]; then
    echo "✓ Model ${ENTREPOT_MODEL_NAME} spawned in Gazebo at ($X, $Y, $Z)"
else
    echo "✗ Failed to spawn model in Gazebo"
    exit 1
fi

echo -e "\n=================================================="
echo "  ✓ Warehouse spawned successfully!"
echo "=================================================="
