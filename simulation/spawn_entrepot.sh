#!/bin/bash
###############################################################################
# Spawn Drone Script - Artefac Drone Defense
# Adds a new drone to the running simulation dynamically
#
# Usage:
#   bash spawn_livraison.sh <drone_num> [x] [y] [z]
#
# Arguments:
#   livraison_num : livraison number (0, 1, 2, 3, ...)
#   x, y, z   : Spawn position in meters (optional, defaults based on drone_num)
#
# Examples:
#   bash spawn_drone.sh 0          # Spawn drone_1 at default position
#   bash spawn_drone.sh 1 5 5 0.5  # Spawn drone_2 at (5, 5, 0.5)
#
# What it does:
#   1. Spawns x500_N model in Gazebo at specified position
#   2. Starts PX4 SITL instance N with MAVLink on port 14540+N
#   3. Launches MAVROS + vision_bridge + mqtt_bridge for /drone_N/ namespace
#
# Prerequisites:
#   - Gazebo simulation running
#   - ROS2 workspace sourced
#   - MQTT broker available
###############################################################################

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <entr_num> [x] [y] [z]"
    echo "Example: $0 0        # Spawn entrepot_1 at default position"
    echo "Example: $0 1 5 5 0.5  # Spawn entrepot_2 at (5, 5, 0.5)"
    exit 1
fi

ENTR_NUM=$1
ENTR_ID="entrepot_$((ENTR_NUM + 1))"  # drone_1, drone_2, drone_3, ...
ENTR_NAME="entrepot_${ENTR_NUM}"        # x500_0, x500_1, x500_2, ...

# Position (defaults to grid pattern)
X=${2:-$((ENTR_NUM * 3))}  # 0, 3, 6, 9, ... (using bash arithmetic)
Y=${3:-0}
Z=${4:-0.5}

# MAVLink ports
FCU_PORT=$((14540 + ENTR_NUM))
GCS_PORT=$((14580 + ENTR_NUM))
SYSTEM_ID=$((ENTR_NUM + 1))

# MQTT broker
MQTT_BROKER=${MQTT_BROKER:-localhost}

echo "=================================================="
echo "  Spawning Livraison ${ENTR_ID}"
echo "=================================================="
echo "livraison Name:  $ENTR_NAME"
echo "Position:    ($X, $Y, $Z)"
echo "System ID:   $SYSTEM_ID"
echo "FCU Port:    $FCU_PORT"
echo "GCS Port:    $GCS_PORT"
echo "Namespace:   /${ENTR_ID}/"
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

