#!/bin/bash
###############################################################################
# Despawn Entrepôt Script - Artefac Drone Defense
# Removes an entrepôt (warehouse) from the running simulation dynamically
#
# Usage:
#   bash despawn_entrepot.sh <entrepot_num>
#
# Arguments:
#   entrepot_num : Entrepôt number to remove (0, 1, 2, 3, ...)
#
# Examples:
#   bash despawn_entrepot.sh 0  # Remove entrepot_1
#   bash despawn_entrepot.sh 2  # Remove entrepot_3
#
# What it does:
#   1. Removes entrepot model from Gazebo
#
# Prerequisites:
#   - Entrepôt was spawned with spawn_entrepot.sh
###############################################################################

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <entrepot_num>"
    echo "Example: $0 0  # Remove entrepot_1"
    exit 1
fi

ENTR_NUM=$1
ENTR_ID="entrepot_$((ENTR_NUM + 1))"
ENTR_NAME="entrepot_${ENTR_NUM}"

echo "=================================================="
echo "  Despawning Entrepôt ${ENTR_ID}"
echo "=================================================="
echo "Model Name:  $ENTR_NAME"
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
  --req "name: \"${ENTR_NAME}\", type: 2" 2>&1)

# Check result
if echo "$REMOVE_OUTPUT" | grep -q "data: true"; then
    echo "✓ Model ${ENTR_NAME} removed from Gazebo"
else
    echo "⚠ Model ${ENTR_NAME} not found in Gazebo (may have been removed already)"
fi

echo ""
echo "=================================================="
echo "  ✓ Entrepôt ${ENTR_ID} despawned successfully!"
echo "=================================================="

