#!/bin/bash
###############################################################################
# Spawn Drone Script - Artefac Drone Defense
# Adds a new drone to the running simulation dynamically
#
# Usage:
#   bash spawn_drone.sh <drone_num> [x] [y] [z]
#
# Arguments:
#   drone_num : Drone number (0, 1, 2, 3, ...)
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
    echo "Usage: $0 <zone_num> [x] [y] [z]"
    echo "Example: $0 0        # Spawn zone_1 at default position"
    echo "Example: $0 1 5 5 0.5  # Spawn zone_2 at (5, 5, 0.5)"
    exit 1
fi

LIVRAISON_NUM=$1
LIVRAISON_ID="livraison_$((LIVRAISON_NUM + 1))"  # zone_1, zone_2, zone_3, ...
LIVRAISON_NAME="zone_${LIVRAISON_NUM}"        # zone_0, zone_1, zone_2, ...

# Position (defaults to grid pattern)
X=${2:-$((ZONE_NUM * 3))}  # 0, 3, 6, 9, ... (using bash arithmetic)
Y=${3:-0}
Z=${4:-0.5}

# MAVLink ports
FCU_PORT=$((14540 + LIVRAISON_NUM))
GCS_PORT=$((14580 + LIVRAISON_NUM))
SYSTEM_ID=$((LIVRAISON_NUM + 1))

# MQTT broker
MQTT_BROKER=${MQTT_BROKER:-localhost}

echo "=================================================="
echo "  Spawning Zone ${LIVRAISON_ID}"
echo "=================================================="
echo "Model Name:  $LIVRAISON_NAME"
echo "Position:    ($X, $Y, $Z)"
echo "System ID:   $SYSTEM_ID"
echo "FCU Port:    $FCU_PORT"
echo "GCS Port:    $GCS_PORT"
echo "Namespace:   /${LIVRAISON_ID}/"
echo "=================================================="

# Step 1: Spawn model in Gazebo
echo -e "\n[1/1] Spawning model in Gazebo..."

# Check if Gazebo server is accessible (works across containers with network_mode: host)
if ! timeout 5 gz service --list > /dev/null 2>&1; then
    echo "ERROR: Gazebo simulation is not accessible!"
    echo "  (Gazebo server might be running in a different container)"
    exit 1
fi


#TODO changer le sdf
# Construct SDF as single-line string (protobuf text format doesn't support multiline)
SDF_CONTENT="<?xml version=\\\"1.0\\\"?><sdf version=\\\"1.9\\\"><model name=\\\"${MODEL_NAME}\\\"><pose>${X} ${Y} ${Z} 0 0 0</pose><include><uri>model://Sphere</uri></include></model></sdf>"

# Spawn via gz service
gz service -s /world/default/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --req "sdf: \"${SDF_CONTENT}\", name: \"${LIVRAISON_NAME}\""

if [ $? -eq 0 ]; then
    echo "✓ Model ${LIVRAISON_NAME} spawned in Gazebo at ($X, $Y, $Z)"
else
    echo "✗ Failed to spawn model in Gazebo"
    exit 1
fi

