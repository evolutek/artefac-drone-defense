#!/bin/bash
###############################################################################
# Spawn PX4 Script - Artefac Drone Defense
# Spawns Gazebo model and starts PX4 SITL instance
# RUNS IN: simulation container
#
# Usage:
#   bash spawn_px4.sh <drone_num> [x] [y] [z] [gazebo_model] [autostart_id]
#
# Arguments:
#   drone_num     : Drone number (0, 1, 2, 3, ...)
#   x, y, z       : Spawn position in meters (optional, defaults based on drone_num)
#   gazebo_model  : Gazebo model name (optional, default: x500)
#   autostart_id  : PX4 airframe autostart ID (optional, default: 4001)
#
# Examples:
#   bash spawn_px4.sh 0                  # Spawn drone_1 at default position (x500)
#   bash spawn_px4.sh 1 5 5 0.5          # Spawn drone_2 at (5, 5, 0.5) (x500)
#   bash spawn_px4.sh 0 0 0 0.5 x500_depth 4002  # Spawn drone_1 with depth camera
#
# What it does:
#   1. Spawns x500_N model in Gazebo at specified position
#   2. Starts PX4 SITL instance N with MAVLink on port 14540+N
#
# Prerequisites:
#   - Gazebo simulation running
#   - PX4-Autopilot binaries available
###############################################################################

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <drone_num> [x] [y] [z] [gazebo_model] [autostart_id]"
    echo "Example: $0 0                    # Spawn drone_1 at default position"
    echo "Example: $0 1 5 5 0.5            # Spawn drone_2 at (5, 5, 0.5)"
    echo "Example: $0 0 0 0 0.5 x500_depth 4002  # Spawn drone_1 with depth camera"
    exit 1
fi

DRONE_NUM=$1
DRONE_ID="drone_$((DRONE_NUM + 1))"  # drone_1, drone_2, drone_3, ...

# Position (defaults to grid pattern)
X=${2:-$((DRONE_NUM * 3))}  # 0, 3, 6, 9, ... (using bash arithmetic)
Y=${3:-0}
Z=${4:-0.5}

# Model configuration (defaults to standard x500)
GAZEBO_MODEL=${5:-x500}          # Gazebo model name (x500, x500_depth, etc.)
AUTOSTART_ID=${6:-4001}          # PX4 airframe autostart ID

# Model name for Gazebo (e.g., x500_0, x500_depth_1)
MODEL_NAME="${GAZEBO_MODEL}_${DRONE_NUM}"

# Derive PX4_SIM_MODEL from GAZEBO_MODEL (add gz_ prefix)
PX4_SIM_MODEL="gz_${GAZEBO_MODEL}"

# MAVLink ports
FCU_PORT=$((14540 + DRONE_NUM))
GCS_PORT=$((14580 + DRONE_NUM))
SYSTEM_ID=$((DRONE_NUM + 1))

echo "==================================================="
echo "  Spawning Drone ${DRONE_ID} (PX4 Component)"
echo "==================================================="
echo "Gazebo Model:  $GAZEBO_MODEL"
echo "Model Name:    $MODEL_NAME"
echo "Autostart ID:  $AUTOSTART_ID"
echo "PX4 Model:     $PX4_SIM_MODEL"
echo "Position:      ($X, $Y, $Z)"
echo "System ID:     $SYSTEM_ID"
echo "FCU Port:      $FCU_PORT"
echo "GCS Port:      $GCS_PORT"
echo "==================================================="

# Step 1: Spawn model in Gazebo
echo ""
echo "[1/2] Spawning model in Gazebo..."

# Check if Gazebo server is accessible
if ! timeout 5 gz service --list > /dev/null 2>&1; then
    echo "ERROR: Gazebo simulation is not accessible!"
    exit 1
fi

# Construct SDF as single-line string (protobuf text format doesn't support multiline)
# Use dynamic GAZEBO_MODEL instead of hardcoded "x500"
SDF_CONTENT="<?xml version=\\\"1.0\\\"?><sdf version=\\\"1.9\\\"><model name=\\\"${MODEL_NAME}\\\"><pose>${X} ${Y} ${Z} 0 0 0</pose><include><uri>model://${GAZEBO_MODEL}</uri></include></model></sdf>"

# Spawn via gz service
gz service -s /world/default/create \
  --reqtype gz.msgs.EntityFactory \
  --reptype gz.msgs.Boolean \
  --req "sdf: \"${SDF_CONTENT}\", name: \"${MODEL_NAME}\""

if [ $? -eq 0 ]; then
    echo "✓ Model ${MODEL_NAME} spawned in Gazebo at ($X, $Y, $Z)"
else
    echo "✗ Failed to spawn model in Gazebo"
    exit 1
fi

# Step 2: Start PX4 SITL
echo ""
echo "[2/2] Starting PX4 SITL instance ${DRONE_NUM}..."

# Verify PX4 binary exists
if [ ! -f "/root/PX4-Autopilot/build/px4_sitl_default/bin/px4" ]; then
    echo "ERROR: PX4 binary not found at /root/PX4-Autopilot/build/px4_sitl_default/bin/px4"
    echo "This script must run in the 'simulation' container"
    exit 1
fi

cd /root/PX4-Autopilot

# Create log directory if not exists
mkdir -p /root/.ros/log

# Launch PX4 with instance-specific config (dynamic model and autostart ID)
PX4_SYS_AUTOSTART=${AUTOSTART_ID} \
PX4_GZ_MODEL_NAME=${MODEL_NAME} \
PX4_SIM_MODEL=${PX4_SIM_MODEL} \
./build/px4_sitl_default/bin/px4 -i ${DRONE_NUM} -d \
  > /root/.ros/log/px4_${MODEL_NAME}.log 2>&1 &

PX4_PID=$!
echo "✓ PX4 SITL started (PID: $PX4_PID, instance: $DRONE_NUM)"
echo "  MAVLink: udp://:${FCU_PORT}@127.0.0.1:${GCS_PORT}"
echo "  Logs: /root/.ros/log/px4_${MODEL_NAME}.log"

# Save PID for cleanup
echo $PX4_PID > /tmp/px4_${DRONE_NUM}.pid

echo ""
echo "==================================================="
echo "  ✓ PX4 component spawned successfully!"
echo "==================================================="
echo ""
echo "Next step: Run spawn_ros2.sh ${DRONE_NUM} in ros2_integration container"
echo "==================================================="
