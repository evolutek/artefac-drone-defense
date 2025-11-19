#!/bin/bash
###############################################################################
# Despawn Exclusion Zone Script - Artefac Drone Defense
# Removes an exclusion zone visual marker from Gazebo simulation
#
# Usage:
#   bash despawn_zone.sh <zone_id>
#
# Arguments:
#   zone_id : Zone identifier to remove (e.g., "zone_0", "zone_alpha")
#
# Examples:
#   bash despawn_zone.sh zone_0
#   bash despawn_zone.sh zone_alpha
#
# What it does:
#   1. Removes the zone model from Gazebo
#   2. Cleans up any temporary files
#
# Prerequisites:
#   - Gazebo simulation running
#   - Zone was spawned with spawn_zone.sh
###############################################################################

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <zone_id>"
    echo "Example: $0 zone_0"
    exit 1
fi

ZONE_ID=$1

echo "=================================================="
echo "  Despawning Exclusion Zone"
echo "=================================================="
echo "Zone ID:     $ZONE_ID"
echo "=================================================="

echo ""
echo "[1/2] Removing zone from Gazebo..."

# Remove model from Gazebo using gz service
if gz service -s /world/default/remove \
    --reqtype gz.msgs.Entity \
    --reptype gz.msgs.Boolean \
    --timeout 5000 \
    --req "name: \"$ZONE_ID\", type: MODEL" 2>&1 | grep -q "data: true"; then

    echo "✓ Zone removed from Gazebo"
else
    echo "✗ Failed to remove zone from Gazebo (may not exist)"
    # Don't exit - continue cleanup
fi

echo ""
echo "[2/2] Cleaning up temporary files..."

# Clean up any temporary SDF files
TMP_SDF="/tmp/${ZONE_ID}.sdf"
if [ -f "$TMP_SDF" ]; then
    rm -f "$TMP_SDF"
    echo "✓ Removed temporary SDF file"
else
    echo "  (no temp files to clean)"
fi

echo ""
echo "=================================================="
echo "  Zone $ZONE_ID Removed Successfully!"
echo "=================================================="

exit 0
