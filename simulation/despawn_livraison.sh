#!/bin/bash
###############################################################################
# Despawn Delivery (Livraison) Script - Artefac Drone Defense
# Removes a delivery package model from Gazebo simulation
#
# Usage:
#   bash despawn_livraison.sh <livraison_model_name>
#
# Arguments:
#   livraison_model_name : Gazebo model name to remove (e.g., "livraison_package_alpha")
#
# Examples:
#   bash despawn_livraison.sh livraison_package_alpha
#   bash despawn_livraison.sh livraison_blood_delivery
#
# What it does:
#   1. Removes the delivery model from Gazebo by model name
#
# Prerequisites:
#   - Gazebo simulation running
#   - Delivery was spawned with spawn_livraison.sh
###############################################################################

set -e

# ============================================================================
# Argument Parsing
# ============================================================================

if [ $# -lt 1 ]; then
    echo "Usage: $0 <livraison_model_name>"
    echo "Example: $0 livraison_package_alpha  # Remove delivery with this model name"
    exit 1
fi

LIVRAISON_MODEL_NAME=$1

# ============================================================================
# Status Output
# ============================================================================

echo "=================================================="
echo "  Despawning Delivery (Livraison)"
echo "=================================================="
echo "Model Name:  $LIVRAISON_MODEL_NAME"
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
  --req "name: \"${LIVRAISON_MODEL_NAME}\", type: 2" 2>&1)

# Check result
if echo "$REMOVE_OUTPUT" | grep -q "data: true"; then
    echo "✓ Model ${LIVRAISON_MODEL_NAME} removed from Gazebo"
else
    echo "⚠ Model ${LIVRAISON_MODEL_NAME} not found in Gazebo (may have been removed already)"
fi

echo -e "\n=================================================="
echo "  ✓ Delivery despawned successfully!"
echo "=================================================="
