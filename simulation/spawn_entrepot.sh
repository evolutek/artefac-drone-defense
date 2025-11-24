#!/bin/bash
###############################################################################
# Spawn Exclusion entrepot Script - Artefac Drone Defense
# Creates a visual marker for exclusion entrepots in Gazebo simulation
#
# Usage:
#   bash spawn_entrepot.sh <entrepot_num>  <x> <y> <z> <radius> <R> <G> <B>
#
# Arguments:
#   entrepot_id : Unique entrepot identifier (e.g., "entrepot_0", "entrepot_alpha")
#   name    : Human-readable entrepot name (e.g., "Jamming entrepot Alpha")
#   type    : entrepot type - "jamming", "no-fly", or "restricted"
#   x, y, z : Center position in meters
#   radius  : Radius in meters
#
# Examples:
#   bash spawn_entrepot.sh entrepot_0 "Jamming Alpha" jamming 10 10 0 15
#   bash spawn_entrepot.sh entrepot_1 "No-Fly Beta" no-fly 20 5 0 10
#
# What it does:
#   1. Generates SDF model from template with specified radius and color
#   2. Spawns semi-transparent cylinder marker in Gazebo
#   3. Visual marker only - no physics collision
#
# Prerequisites:
#   - Gazebo simulation running
#   - gz command available
###############################################################################

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <entrepot_num> [name] [x] [y] [z] [radius] [R] [G] [B] [A]"
    echo "Example: $0 0 'entrepot Alpha'        # Spawn entrepot_1 with name at default position"
    echo "Example: $0 1 'entrepot Beta' 5 5 0.5 2  # Spawn entrepot_2 at (5, 5, 0.5)"
    exit 1
fi

entrepot_NUM=$1
USER_entrepot_NAME=${2:-"unnamed_${entrepot_NUM}"}  # User-provided entrepot name

# Normalize entrepot name for Gazebo model (replace spaces with underscores, lowercase)
NORMALIZED_NAME=$(echo "$USER_entrepot_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd '[:alnum:]_')

# Gazebo model name with entrepot_ prefix for easy discovery
entrepot_MODEL_NAME="entrepot_${NORMALIZED_NAME}"
entrepot_ID="entrepot_$((entrepot_NUM))"  # Internal ID for tracking (entrepot_0, entrepot_1, ...)

# Position (defaults to grid pattern)
X=${3:-$((entrepot_NUM * 3))}  # 0, 3, 6, 9, ... (using bash arithmetic)
Y=${4:-0}
Z=${5:-0.5}
RADIUS=${6:-1}
R=${7:-1}
G=${8:-0}
B=${9:-0}
A=${10:-0.75}

# MAVLink ports
FCU_PORT=$((14540 + entrepot_NUM))
GCS_PORT=$((14580 + entrepot_NUM))
SYSTEM_ID=$((entrepot_NUM + 1))

# MQTT broker
MQTT_BROKER=${MQTT_BROKER:-localhost}

echo "=================================================="
echo "  Spawning entrepot ${entrepot_ID}"
echo "=================================================="
echo "User Name:   $USER_entrepot_NAME"
echo "Model Name:  $entrepot_MODEL_NAME"
echo "Position:    ($X, $Y, $Z)"
echo "System ID:   $SYSTEM_ID"
echo "FCU Port:    $FCU_PORT"
echo "GCS Port:    $GCS_PORT"
echo "Namespace:   /${entrepot_ID}/"
echo "=================================================="

# Step 1: Spawn model in Gazebo
echo -e "\n[1/1] Spawning model in Gazebo..."

# Check if Gazebo server is accessible (works across containers with network_mode: host)
if ! timeout 5 gz service --list > /dev/null 2>&1; then
    echo "ERROR: Gazebo simulation is not accessible!"
    echo "  (Gazebo server might be running in a different container)"
    exit 1
fi

WORLD_NAME=$(gz service --list | grep -oP '/world/\K[^/]+' | head -1)
if [ -z "$WORLD_NAME" ]; then
    echo "ERROR: Could not detect Gazebo world name"
    exit 1
fi

# Construct SDF as single-line string (protobuf text format doesn't support multiline)
SDF_CONTENT="<sdf version=\\\"1.9\\\"><model name=\\\"$entrepot_MODEL_NAME\\\"><pose>${X} ${Y} ${Z} 0 0 0</pose><include><uri>model://shelf</uri></include></model></sdf>"

# Spawn via gz service
gz service -s /world/$WORLD_NAME/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --req "sdf: \"${SDF_CONTENT}\", name: \"${entrepot_MODEL_NAME}\""

if [ $? -eq 0 ]; then
    echo "✓ Model ${entrepot_MODEL_NAME} spawned in Gazebo at ($X, $Y, $Z)"
else
    echo "✗ Failed to spawn model in Gazebo"
    exit 1
fi

#TODO comunication avec le backend
