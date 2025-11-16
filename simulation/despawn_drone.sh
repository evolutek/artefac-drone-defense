#!/bin/bash
###############################################################################
# Despawn Drone Script - Artefac Drone Defense
# Removes a drone from the running simulation dynamically
#
# Usage:
#   bash despawn_drone.sh <drone_num>
#
# Arguments:
#   drone_num : Drone number to remove (0, 1, 2, 3, ...)
#
# Examples:
#   bash despawn_drone.sh 0  # Remove drone_1
#   bash despawn_drone.sh 2  # Remove drone_3
#
# What it does:
#   1. Kills MAVROS + bridges processes for this drone
#   2. Kills PX4 SITL instance
#   3. Removes x500_N model from Gazebo
#
# Prerequisites:
#   - Drone was spawned with spawn_drone.sh
###############################################################################

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <drone_num>"
    echo "Example: $0 0  # Remove drone_1"
    exit 1
fi

DRONE_NUM=$1
DRONE_ID="drone_$((DRONE_NUM + 1))"
MODEL_NAME="x500_${DRONE_NUM}"

echo "=================================================="
echo "  Despawning Drone ${DRONE_ID}"
echo "=================================================="
echo "Model Name:  $MODEL_NAME"
echo "Namespace:   /${DRONE_ID}/"
echo "=================================================="

# Step 1: Kill ROS2 processes (MAVROS + bridges)
echo ""
echo "[1/3] Stopping ROS2 nodes..."

# Read PIDs from files if they exist
MAVROS_PID=""
BRIDGES_PID=""

if [ -f "/tmp/mavros_${DRONE_NUM}.pid" ]; then
    MAVROS_PID=$(cat /tmp/mavros_${DRONE_NUM}.pid)
fi

if [ -f "/tmp/bridges_${DRONE_NUM}.pid" ]; then
    BRIDGES_PID=$(cat /tmp/bridges_${DRONE_NUM}.pid)
fi

# Kill processes
KILLED=0

if [ -n "$MAVROS_PID" ] && kill -0 $MAVROS_PID 2>/dev/null; then
    echo "  → Killing MAVROS (PID: $MAVROS_PID)..."
    kill -SIGINT $MAVROS_PID 2>/dev/null || true
    KILLED=$((KILLED + 1))
fi

if [ -n "$BRIDGES_PID" ] && kill -0 $BRIDGES_PID 2>/dev/null; then
    echo "  → Killing bridges (PID: $BRIDGES_PID)..."
    kill -SIGINT $BRIDGES_PID 2>/dev/null || true
    KILLED=$((KILLED + 1))
fi

# Fallback: kill by namespace pattern (if PIDs not found)
if [ $KILLED -eq 0 ]; then
    echo "  → PIDs not found, killing by namespace pattern..."
    pkill -f "namespace:=${DRONE_ID}" 2>/dev/null || true
fi

# Wait for graceful shutdown
sleep 2

# Force kill if still running
if [ -n "$MAVROS_PID" ]; then
    kill -SIGKILL $MAVROS_PID 2>/dev/null || true
fi
if [ -n "$BRIDGES_PID" ]; then
    kill -SIGKILL $BRIDGES_PID 2>/dev/null || true
fi

echo "✓ ROS2 nodes stopped"

# Cleanup PID files
rm -f /tmp/mavros_${DRONE_NUM}.pid
rm -f /tmp/bridges_${DRONE_NUM}.pid

# Step 2: Kill PX4 SITL
echo ""
echo "[2/3] Stopping PX4 SITL..."

PX4_PID=""
if [ -f "/tmp/px4_${DRONE_NUM}.pid" ]; then
    PX4_PID=$(cat /tmp/px4_${DRONE_NUM}.pid)
fi

if [ -n "$PX4_PID" ] && kill -0 $PX4_PID 2>/dev/null; then
    echo "  → Killing PX4 SITL (PID: $PX4_PID)..."
    kill -SIGINT $PX4_PID 2>/dev/null || true
    sleep 1
    kill -SIGKILL $PX4_PID 2>/dev/null || true
    echo "✓ PX4 SITL stopped"
else
    echo "  → PID not found, killing by instance number..."
    pkill -f "px4 -i ${DRONE_NUM}" 2>/dev/null || true
    echo "✓ PX4 SITL stopped (fallback)"
fi

rm -f /tmp/px4_${DRONE_NUM}.pid

# Step 3: Remove model from Gazebo
echo ""
echo "[3/3] Removing model from Gazebo..."

# Check if Gazebo is running
if ! pgrep -x "gz sim" > /dev/null; then
    echo "⚠ Gazebo simulation is not running, skipping model removal"
else
    # Remove via gz service
    gz service -s /world/default/remove \
      --reqtype gz.msgs.Entity \
      --reptype gz.msgs.Boolean \
      --req "name: \"${MODEL_NAME}\", type: 2" 2>/dev/null || true

    if [ $? -eq 0 ]; then
        echo "✓ Model ${MODEL_NAME} removed from Gazebo"
    else
        echo "⚠ Failed to remove model from Gazebo (may not exist)"
    fi
fi

# Cleanup log files (optional)
echo ""
echo "Cleaning up log files..."
rm -f /tmp/mavros_${DRONE_ID}.log
rm -f /tmp/bridges_${DRONE_ID}.log
rm -f /root/.ros/log/px4_${MODEL_NAME}.log

echo ""
echo "=================================================="
echo "  ✓ Drone ${DRONE_ID} despawned successfully!"
echo "=================================================="
echo ""
echo "Remaining drones can be listed with:"
echo "  ros2 topic list | grep /drone_"
echo "  gz topic -l | grep x500_"
echo "=================================================="
