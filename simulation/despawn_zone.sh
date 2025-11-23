#!/bin/bash
###############################################################################
# Despawn Exclusion Zone Script - Artefac Drone Defense
# Removes an exclusion zone visual marker from Gazebo simulation
#
# Usage:
#   bash despawn_zone.sh <zone_model_name>
#
# Arguments:
#   zone_model_name : Gazebo model name to remove (e.g., "zone_jamming_alpha")
#
# Examples:
#   bash despawn_zone.sh zone_jamming_alpha
#   bash despawn_zone.sh zone_no_fly_beta
#
# What it does:
#   1. Removes the zone model from Gazebo by model name
#
# Prerequisites:
#   - Gazebo simulation running
#   - Zone was spawned with spawn_zone.sh
###############################################################################

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <zone_model_name>"
    echo "Example: $0 zone_jamming_alpha  # Remove zone with this model name"
    exit 1
fi

ZONE_MODEL_NAME=$1

echo "=================================================="
echo "  Despawning Zone"
echo "=================================================="
echo "Model Name:  $ZONE_MODEL_NAME"
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
  --req "name: \"${ZONE_MODEL_NAME}\", type: 2" 2>&1)

# Check result
if echo "$REMOVE_OUTPUT" | grep -q "data: true"; then
    echo "✓ Model ${ZONE_MODEL_NAME} removed from Gazebo"
else
    echo "⚠ Model ${ZONE_MODEL_NAME} not found in Gazebo (may have been removed already)"
fi

echo -e "\n=================================================="
echo "  ✓ Zone ${ZONE_MODEL_NAME} despawned successfully!"
echo "=================================================="

