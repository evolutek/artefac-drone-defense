#!/bin/bash
###############################################################################
# Spawn Exclusion Zone Script - Artefac Drone Defense
# Creates a visual marker for exclusion zones in Gazebo simulation
#
# Usage:
#   bash spawn_zone.sh <zone_num>  <x> <y> <z> <radius> <R> <G> <B>
#
# Arguments:
#   zone_id : Unique zone identifier (e.g., "zone_0", "zone_alpha")
#   name    : Human-readable zone name (e.g., "Jamming Zone Alpha")
#   type    : Zone type - "jamming", "no-fly", or "restricted"
#   x, y, z : Center position in meters
#   radius  : Radius in meters
#
# Examples:
#   bash spawn_zone.sh zone_0 "Jamming Alpha" jamming 10 10 0 15
#   bash spawn_zone.sh zone_1 "No-Fly Beta" no-fly 20 5 0 10
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
    echo "Usage: $0 <zone_num> [x] [y] [z] <radius>"
    echo "Example: $0 0        # Spawn zone_1 at default position"
    echo "Example: $0 1 5 5 0.5 2  # Spawn zone_2 at (5, 5, 0.5)"
    exit 1
fi

ZONE_NUM=$1
ZONE_ID="zone_$((ZONE_NUM + 1))"  # zone_1, zone_2, zone_3, ...
ZONE_NAME="zone_${ZONE_NUM}"        # zone_0, zone_1, zone_2, ...

# Position (defaults to grid pattern)
X=${2:-$((ZONE_NUM * 3))}  # 0, 3, 6, 9, ... (using bash arithmetic)
Y=${3:-0}
Z=${4:-0.5}
RADIUS=${5:-1}
R=${6:-1}
G=${7:-0}
B=${8:-0}
A=${9:-0.75}

# MAVLink ports
FCU_PORT=$((14540 + ZONE_NUM))
GCS_PORT=$((14580 + ZONE_NUM))
SYSTEM_ID=$((ZONE_NUM + 1))

# MQTT broker
MQTT_BROKER=${MQTT_BROKER:-localhost}

echo "=================================================="
echo "  Spawning Zone ${ZONE_ID}"
echo "=================================================="
echo "Model Name:  $ZONE_NAME"
echo "Position:    ($X, $Y, $Z)"
echo "System ID:   $SYSTEM_ID"
echo "FCU Port:    $FCU_PORT"
echo "GCS Port:    $GCS_PORT"
echo "Namespace:   /${ZONE_ID}/"
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
SDF_CONTENT="<?xml version=\\\"1.0\\\"?><sdf version=\\\"1.9\\\"><model name=\\\"${ZONE_NAME}\\\"><pose>${X} ${Y} ${Z} 0 0 0</pose><model name=\\\"sphere\\\"><static>true</static><link name=\\\"sphere_link\\\"><visual name=\\\"sphere_visual\\\"><geometry><sphere><radius>${RADIUS}</radius></sphere></geometry><material><ambient>$R $G $B $A</ambient><diffuse>$R $G $B $A</diffuse><specular>0.2 0.2 0.2 1</specular><emissive>0 0 0 1</emissive></material></visual></link></model></model></sdf>"

# Spawn via gz service
gz service -s /world/$WORLD_NAME/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --req "sdf: \"${SDF_CONTENT}\", name: \"${ZONE_NAME}\""

if [ $? -eq 0 ]; then
    echo "✓ Model ${ZONE_NAME} spawned in Gazebo at ($X, $Y, $Z)"
else
    echo "✗ Failed to spawn model in Gazebo"
    exit 1
fi

#TODO comunication avec le backend
