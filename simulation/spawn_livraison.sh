#!/bin/bash
###############################################################################
# Spawn Exclusion livraison Script - Artefac Drone Defense
# Creates a visual marker for exclusion livraisons in Gazebo simulation
#
# Usage:
#   bash spawn_livraison.sh <livraison_num>  <x> <y> <z> <radius> <R> <G> <B>
#
# Arguments:
#   livraison_id : Unique livraison identifier (e.g., "livraison_0", "livraison_alpha")
#   name    : Human-readable livraison name (e.g., "Jamming livraison Alpha")
#   type    : livraison type - "jamming", "no-fly", or "restricted"
#   x, y, z : Center position in meters
#   radius  : Radius in meters
#
# Examples:
#   bash spawn_livraison.sh livraison_0 "Jamming Alpha" jamming 10 10 0 15
#   bash spawn_livraison.sh livraison_1 "No-Fly Beta" no-fly 20 5 0 10
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
    echo "Usage: $0 <livraison_num> [name] [x] [y] [z] [radius] [R] [G] [B] [A]"
    echo "Example: $0 0 'livraison Alpha'        # Spawn livraison_1 with name at default position"
    echo "Example: $0 1 'livraison Beta' 5 5 0.5 2  # Spawn livraison_2 at (5, 5, 0.5)"
    exit 1
fi

livraison_NUM=$1
USER_livraison_NAME=${2:-"unnamed_${livraison_NUM}"}  # User-provided livraison name

# Normalize livraison name for Gazebo model (replace spaces with underscores, lowercase)
NORMALIZED_NAME=$(echo "$USER_livraison_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd '[:alnum:]_')

# Gazebo model name with livraison_ prefix for easy discovery
livraison_MODEL_NAME="livraison_${NORMALIZED_NAME}"
livraison_ID="livraison_$((livraison_NUM))"  # Internal ID for tracking (livraison_0, livraison_1, ...)

# Position (defaults to grid pattern)
X=${3:-$((livraison_NUM * 3))}  # 0, 3, 6, 9, ... (using bash arithmetic)
Y=${4:-0}
Z=${5:-0.5}
RADIUS=${6:-1}
R=${7:-1}
G=${8:-0}
B=${9:-0}
A=${10:-0.75}

# MAVLink ports
FCU_PORT=$((14540 + livraison_NUM))
GCS_PORT=$((14580 + livraison_NUM))
SYSTEM_ID=$((livraison_NUM + 1))

# MQTT broker
MQTT_BROKER=${MQTT_BROKER:-localhost}

echo "=================================================="
echo "  Spawning livraison ${livraison_ID}"
echo "=================================================="
echo "User Name:   $USER_livraison_NAME"
echo "Model Name:  $livraison_MODEL_NAME"
echo "Position:    ($X, $Y, $Z)"
echo "System ID:   $SYSTEM_ID"
echo "FCU Port:    $FCU_PORT"
echo "GCS Port:    $GCS_PORT"
echo "Namespace:   /${livraison_ID}/"
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
SDF_CONTENT="<sdf version=\\\"1.9\\\"><model name=\\\"$livraison_MODEL_NAME\\\"><pose>${X} ${Y} ${Z} 0 0 0</pose><include><uri>model://Mascot</uri></include></model></sdf>"

# Spawn via gz service
gz service -s /world/$WORLD_NAME/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --req "sdf: \"${SDF_CONTENT}\", name: \"${livraison_MODEL_NAME}\""

if [ $? -eq 0 ]; then
    echo "✓ Model ${livraison_MODEL_NAME} spawned in Gazebo at ($X, $Y, $Z)"
else
    echo "✗ Failed to spawn model in Gazebo"
    exit 1
fi

#TODO comunication avec le backend
