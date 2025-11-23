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

LIVR_NUM=$1
LIVR_ID="entrepot_$((LIVR_NUM + 1))"
LIVR_NAME="entrepot_${LIVR_NUM}"

echo "=================================================="
echo "  Despawning entrepot ${LIVR_ID}"
echo "=================================================="
echo "Model Name:  $LIVR_NAME"
echo "Namespace:   /${LIVR_ID}/"
echo "=================================================="

echo -e "\n[1/1] Removing model from Gazebo..."

# Detect world name dynamically (same as spawn script)
WORLD_NAME=$(gz service --list | grep -oP '/world/\K[^/]+' | head -1)
if [ -z "$WORLD_NAME" ]; then
    echo "ERROR: Could not detect Gazebo world name"
    exit 1
fi
echo "Detected Gazebo world: $WORLD_NAME"

# Remove via gz service (ignore errors if model doesn't exist)
REMOVE_OUTPUT=$(gz service -s /world/${WORLD_NAME}/remove \
  --reqtype gz.msgs.Entity \
  --reptype gz.msgs.Boolean \
  --timeout 5000 \
  --req "name: \"${LIVR_NAME}\", type: 2" 2>&1)

# Check result
if echo "$REMOVE_OUTPUT" | grep -q "data: true"; then
    echo "✓ Model ${LIVR_NAME} removed from Gazebo"
else
    echo "⚠ Model ${LIVR_NAME} not found in Gazebo (may have been removed already)"
fi

# Cleanup log files and param files (optional)
echo ""
echo "Cleaning up log files and parameter files..."
rm -f /tmp/mavros_${LIVR_ID}.log
rm -f /tmp/bridges_${LIVR_ID}.log
rm -f /root/.ros/log/px4_${LIVR_NAME}.log

# Cleanup orphaned parameter files for this drone
for param_file in /tmp/launch_params_*; do
    if [ -f "$param_file" ] && grep -q "drone_id: ${LIVR_ID}" "$param_file" 2>/dev/null; then
        echo "  → Removing parameter file: $(basename $param_file)"
        rm -f "$param_file"
    fi
done

echo -e "\n=================================================="
echo "  ✓ Livraison ${LIVR_ID} despawned successfully!"
echo "=================================================="

