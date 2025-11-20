#!/bin/bash
###############################################################################
# Spawn ROS2 Script - Artefac Drone Defense
# Launches MAVROS and bridges for a drone
# RUNS IN: ros2_integration container
#
# Usage:
#   bash spawn_ros2.sh <drone_num>
#
# Arguments:
#   drone_num : Drone number (0, 1, 2, 3, ...)
#
# Examples:
#   bash spawn_ros2.sh 0  # Launch MAVROS for drone_1
#   bash spawn_ros2.sh 1  # Launch MAVROS for drone_2
#
# What it does:
#   1. Launches MAVROS for /drone_N/ namespace
#   2. Launches vision_bridge + mqtt_bridge
#
# Prerequisites:
#   - ROS2 workspace sourced
#   - PX4 SITL already running (spawn_px4.sh executed first)
#   - MQTT broker available
###############################################################################

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <drone_num>"
    echo "Example: $0 0  # Launch MAVROS for drone_1"
    exit 1
fi

DRONE_NUM=$1
DRONE_ID="drone_$((DRONE_NUM + 1))"  # drone_1, drone_2, drone_3, ...
MODEL_NAME="x500_${DRONE_NUM}"        # x500_0, x500_1, x500_2, ...

# MAVLink ports
FCU_PORT=$((14540 + DRONE_NUM))
GCS_PORT=$((14580 + DRONE_NUM))
SYSTEM_ID=$((DRONE_NUM + 1))

# MQTT broker
MQTT_BROKER=${MQTT_BROKER:-localhost}

echo "==================================================="
echo "  Launching ROS2 for Drone ${DRONE_ID}"
echo "==================================================="
echo "Namespace:   /${DRONE_ID}/"
echo "FCU URL:     udp://:${FCU_PORT}@127.0.0.1:${GCS_PORT}"
echo "System ID:   $SYSTEM_ID"
echo "MQTT Broker: $MQTT_BROKER"
echo "==================================================="

# Source ROS2 workspace (required when called via subprocess)
echo ""
echo "[1/3] Sourcing ROS2 workspace..."

if [ -f "/opt/ros/humble/setup.bash" ]; then
    source /opt/ros/humble/setup.bash
else
    echo "ERROR: ROS2 Humble not found at /opt/ros/humble/setup.bash"
    exit 1
fi

if [ -f "/root/ros2_ws/install/setup.bash" ]; then
    source /root/ros2_ws/install/setup.bash
fi

# Verify ROS2 is now available
if ! command -v ros2 &> /dev/null; then
    echo "ERROR: ROS2 command not available after sourcing"
    exit 1
fi

echo "✓ ROS2 workspace sourced"

# Create log directory if not exists
mkdir -p /tmp

# Launch MAVROS
echo ""
echo "[2/3] Launching MAVROS..."

ros2 launch mavros_launcher px4_sitl.launch.py \
    namespace:=${DRONE_ID} \
    fcu_url:="udp://:${FCU_PORT}@127.0.0.1:${GCS_PORT}" \
    system_id:=${SYSTEM_ID} \
    tgt_system:=${SYSTEM_ID} \
    use_sim_time:=true \
    > /tmp/mavros_${DRONE_ID}.log 2>&1 &

MAVROS_PID=$!
echo "✓ MAVROS launched (PID: $MAVROS_PID)"
echo "  Logs: /tmp/mavros_${DRONE_ID}.log"
echo $MAVROS_PID > /tmp/mavros_${DRONE_NUM}.pid

# Wait for MAVROS services (timeout 30s)
echo ""
echo "[3/3] Waiting for MAVROS services..."
TIMEOUT=30
ELAPSED=0
until ros2 service list 2>/dev/null | grep -q "/${DRONE_ID}/mavros_node/arming"; do
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "⚠ MAVROS services not available after ${TIMEOUT}s"
        echo "  Continuing anyway (services may appear later)"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if ros2 service list 2>/dev/null | grep -q "/${DRONE_ID}/mavros_node/arming"; then
    echo "✓ MAVROS services ready!"

    # Enable vision pose
    ros2 param set /${DRONE_ID}/mavros_node global_position.use_vision true 2>/dev/null || true
    echo "✓ Vision pose forwarding enabled"
fi

# Launch bridges
echo ""
echo "Launching Vision Bridge + MQTT Bridge..."

ros2 launch mqtt_bridge mqtt_bridge.launch.py \
    drone_id:=${DRONE_ID} \
    namespace:=${DRONE_ID} \
    model_name:=${MODEL_NAME} \
    mqtt_broker:=${MQTT_BROKER} \
    > /tmp/bridges_${DRONE_ID}.log 2>&1 &

BRIDGES_PID=$!
echo "✓ Bridges launched (PID: $BRIDGES_PID)"
echo "  Logs: /tmp/bridges_${DRONE_ID}.log"
echo $BRIDGES_PID > /tmp/bridges_${DRONE_NUM}.pid

echo ""
echo "==================================================="
echo "  ✓ ROS2 component launched successfully!"
echo "==================================================="
echo ""
echo "ROS2 Topics:"
echo "  /${DRONE_ID}/mavros/state"
echo "  /${DRONE_ID}/mavros/local_position/pose"
echo "  /${DRONE_ID}/mavros/odometry/out"
echo ""
echo "MQTT Topics:"
echo "  drone/${DRONE_ID}/state"
echo "  drone/${DRONE_ID}/telemetry"
echo "  drone/${DRONE_ID}/command"
echo "==================================================="
