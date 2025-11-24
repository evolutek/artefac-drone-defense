#!/bin/bash
###############################################################################
# Despawn Warehouse (Entrepôt) Script - Artefac Drone Defense
# Removes a warehouse model from Gazebo simulation
#
# Usage:
#   bash despawn_entrepot.sh <entrepot_model_name>
#
# Arguments:
#   entrepot_model_name : Gazebo model name to remove (e.g., "entrepot_main_warehouse")
#
# Examples:
#   bash despawn_entrepot.sh entrepot_main_warehouse
#   bash despawn_entrepot.sh entrepot_medical_depot
#
# What it does:
#   1. Removes the warehouse model from Gazebo by model name
#
# Prerequisites:
#   - Gazebo simulation running
#   - Warehouse was spawned with spawn_entrepot.sh
###############################################################################

set -e

# ============================================================================
# Argument Parsing
# ============================================================================

if [ $# -lt 1 ]; then
    echo "Usage: $0 <entrepot_model_name>"
    echo "Example: $0 entrepot_main_warehouse  # Remove warehouse with this model name"
    exit 1
fi

ENTREPOT_MODEL_NAME=$1

# ============================================================================
# Status Output
# ============================================================================

echo "=================================================="
echo "  Despawning Warehouse (Entrepôt)"
echo "=================================================="
echo "Model Name:  $ENTREPOT_MODEL_NAME"
echo "=================================================="

# ============================================================================
# Gazebo Removal
# ============================================================================

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
  --req "name: \"${ENTREPOT_MODEL_NAME}\", type: 2" 2>&1)

# Check result
if echo "$REMOVE_OUTPUT" | grep -q "data: true"; then
    echo "✓ Model ${ENTREPOT_MODEL_NAME} removed from Gazebo"
else
    echo "⚠ Model ${ENTREPOT_MODEL_NAME} not found in Gazebo (may have been removed already)"
fi

echo -e "\n=================================================="
echo "  ✓ Warehouse despawned successfully!"
echo "=================================================="
