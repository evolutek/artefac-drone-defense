#!/bin/bash
###############################################################################
# Despawn Exclusion livraison Script - Artefac Drone Defense
# Removes an exclusion livraison visual marker from Gazebo simulation
#
# Usage:
#   bash despawn_livraison.sh <livraison_model_name>
#
# Arguments:
#   livraison_model_name : Gazebo model name to remove (e.g., "livraison_jamming_alpha")
#
# Examples:
#   bash despawn_livraison.sh livraison_jamming_alpha
#   bash despawn_livraison.sh livraison_no_fly_beta
#
# What it does:
#   1. Removes the livraison model from Gazebo by model name
#
# Prerequisites:
#   - Gazebo simulation running
#   - livraison was spawned with spawn_livraison.sh
###############################################################################

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <livraison_model_name>"
    echo "Example: $0 livraison_jamming_alpha  # Remove livraison with this model name"
    exit 1
fi

livraison_MODEL_NAME=$1
NORMALIZED_NAME=$(echo "$1" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd '[:alnum:]_')
echo "=================================================="
echo "  Despawning livraison"
echo "=================================================="
echo "Model Name:  $livraison_MODEL_NAME"
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
  --req "name: \"${NORMALIZED_NAME}\", type: 2" 2>&1)

# Check result
if echo "$REMOVE_OUTPUT" | grep -q "data: true"; then
    echo "✓ Model ${livraison_MODEL_NAME} removed from Gazebo"
else
    echo "⚠ Model ${livraison_MODEL_NAME} not found in Gazebo (may have been removed already)"
fi

echo -e "\n=================================================="
echo "  ✓ livraison ${livraison_MODEL_NAME} despawned successfully!"
echo "=================================================="

