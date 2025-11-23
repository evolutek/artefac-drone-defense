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
    echo "Usage: $0 <drone_num> [x] [y] [z]"
    echo "Example: $0 0        # Spawn drone_1 at default position"
    echo "Example: $0 1 5 5 0.5  # Spawn drone_2 at (5, 5, 0.5)"
    exit 1
fi

DRONE_NUM=$1
DRONE_ID="drone_$((DRONE_NUM + 1))"  # drone_1, drone_2, drone_3, ...
MODEL_NAME="x500_${DRONE_NUM}"        # x500_0, x500_1, x500_2, ...

# Position (defaults to grid pattern)
X=${2:-$((DRONE_NUM * 3))}  # 0, 3, 6, 9, ... (using bash arithmetic)
Y=${3:-0}
Z=${4:-0.5}

# MAVLink ports
FCU_PORT=$((14540 + DRONE_NUM))
GCS_PORT=$((14580 + DRONE_NUM))
SYSTEM_ID=$((DRONE_NUM + 1))

# MQTT broker
MQTT_BROKER=${MQTT_BROKER:-localhost}

echo "=================================================="
echo "  Spawning Drone ${DRONE_ID}"
echo "=================================================="
echo "Model Name:  $MODEL_NAME"
echo "Position:    ($X, $Y, $Z)"
echo "System ID:   $SYSTEM_ID"
echo "FCU Port:    $FCU_PORT"
echo "GCS Port:    $GCS_PORT"
echo "Namespace:   /${DRONE_ID}/"
echo "=================================================="

# Step 1: Spawn model in Gazebo
echo ""
echo "[1/3] Spawning model in Gazebo..."

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
SDF_CONTENT="<sdf version=\\\"1.9\\\"><model name=\\\"${MODEL_NAME}\\\"><pose>${X} ${Y} ${Z} 0 0 0</pose><include><uri>model://x500</uri></include></model></sdf>"

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

# Step 2: Start PX4 SITL
echo ""
echo "[2/3] Starting PX4 SITL instance ${DRONE_NUM}..."

# Check if container is simulation or ros2_integration
if [ -f "/root/PX4-Autopilot/build/px4_sitl_default/bin/px4" ]; then
    # We're in simulation container
    cd /root/PX4-Autopilot

    # Launch PX4 with instance-specific config
    PX4_SYS_AUTOSTART=4001 \
    PX4_GZ_MODEL_NAME=${MODEL_NAME} \
    PX4_SIM_MODEL=gz_x500 \
    ./build/px4_sitl_default/bin/px4 -i ${DRONE_NUM} -d \
      > /root/.ros/log/px4_${MODEL_NAME}.log 2>&1 &

    PX4_PID=$!
    echo "✓ PX4 SITL started (PID: $PX4_PID, instance: $DRONE_NUM)"
    echo "  Logs: /root/.ros/log/px4_${MODEL_NAME}.log"

    # Save PID for cleanup
    echo $PX4_PID > /tmp/px4_${DRONE_NUM}.pid
else
    echo "⚠ PX4 binary not found. Assuming PX4 is managed externally."
fi

# Step 3: Launch ROS2 nodes (MAVROS + bridges)
echo ""
echo "[3/3] Launching ROS2 nodes (MAVROS + bridges)..."

# Source ROS2 workspace (required when called via subprocess)
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

# Launch MAVROS
echo "  → Launching MAVROS..."
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
echo "  → Waiting for MAVROS services..."
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
echo "  → Launching Vision Bridge + MQTT Bridge..."
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
echo "=================================================="
echo "  ✓ Drone ${DRONE_ID} spawned successfully!"
echo "=================================================="
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
echo ""
echo "To remove this drone:"
echo "  bash despawn_drone.sh ${DRONE_NUM}"
echo "=================================================="
