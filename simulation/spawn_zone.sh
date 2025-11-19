#!/bin/bash
###############################################################################
# Spawn Exclusion Zone Script - Artefac Drone Defense
# Creates a visual marker for exclusion zones in Gazebo simulation
#
# Usage:
#   bash spawn_zone.sh <zone_id> <name> <type> <x> <y> <z> <radius>
#
# Arguments:
#   zone_id : Unique zone identifier (e.g., "zone_0", "zone_alpha")
#   name    : Human-readable zone name (e.g., "Jamming Zone Alpha")
#   type    : Zone type - "jamming", "no-fly", or "restricted"
#   x, y, z : Center position in meters
#   radius  : Radius in meters
#
# Examples:
#   bash spawn_zone.sh zone_0 "Jamming Alpha" jamming 10 10 0 15
#   bash spawn_zone.sh zone_1 "No-Fly Beta" no-fly 20 5 0 10
#
# What it does:
#   1. Generates SDF model from template with specified radius and color
#   2. Spawns semi-transparent cylinder marker in Gazebo
#   3. Visual marker only - no physics collision
#
# Prerequisites:
#   - Gazebo simulation running
#   - gz command available
###############################################################################

set -e

# Check arguments
if [ $# -lt 7 ]; then
    echo "Usage: $0 <zone_id> <name> <type> <x> <y> <z> <radius>"
    echo "Example: $0 zone_0 \"Jamming Alpha\" jamming 10 10 0 15"
    echo ""
    echo "Types:"
    echo "  jamming    - Red cylinder (1.0 0.0 0.0)"
    echo "  no-fly     - Orange cylinder (1.0 0.5 0.0)"
    echo "  restricted - Yellow cylinder (1.0 1.0 0.0)"
    exit 1
fi

ZONE_ID=$1
ZONE_NAME=$2
ZONE_TYPE=$3
CENTER_X=$4
CENTER_Y=$5
CENTER_Z=$6
RADIUS=$7

# Zone visual settings
HEIGHT=50.0  # Fixed height (tall cylinder for visibility)

# Determine color based on type
case "$ZONE_TYPE" in
    jamming)
        COLOR_R="1.0"
        COLOR_G="0.0"
        COLOR_B="0.0"
        ;;
    no-fly)
        COLOR_R="1.0"
        COLOR_G="0.5"
        COLOR_B="0.0"
        ;;
    restricted)
        COLOR_R="1.0"
        COLOR_G="1.0"
        COLOR_B="0.0"
        ;;
    *)
        echo "ERROR: Invalid zone type '$ZONE_TYPE'"
        echo "Valid types: jamming, no-fly, restricted"
        exit 1
        ;;
esac

echo "=================================================="
echo "  Spawning Exclusion Zone"
echo "=================================================="
echo "Zone ID:     $ZONE_ID"
echo "Name:        $ZONE_NAME"
echo "Type:        $ZONE_TYPE"
echo "Center:      ($CENTER_X, $CENTER_Y, $CENTER_Z)"
echo "Radius:      ${RADIUS}m"
echo "Height:      ${HEIGHT}m"
echo "Color:       RGB($COLOR_R, $COLOR_G, $COLOR_B)"
echo "=================================================="

# Path to SDF template
TEMPLATE_PATH="/root/models/exclusion_zone/model.sdf.template"
if [ ! -f "$TEMPLATE_PATH" ]; then
    # Try alternative path in case we're not in container
    TEMPLATE_PATH="$(dirname "$0")/models/exclusion_zone/model.sdf.template"
fi

if [ ! -f "$TEMPLATE_PATH" ]; then
    echo "ERROR: SDF template not found at $TEMPLATE_PATH"
    exit 1
fi

# Generate SDF from template with variable substitution
SDF_CONTENT=$(cat "$TEMPLATE_PATH" | \
    sed "s/ZONE_NAME/$ZONE_ID/g" | \
    sed "s/CENTER_X/$CENTER_X/g" | \
    sed "s/CENTER_Y/$CENTER_Y/g" | \
    sed "s/CENTER_Z/$CENTER_Z/g" | \
    sed "s/ZONE_RADIUS/$RADIUS/g" | \
    sed "s/ZONE_HEIGHT/$HEIGHT/g" | \
    sed "s/ZONE_COLOR_R/$COLOR_R/g" | \
    sed "s/ZONE_COLOR_G/$COLOR_G/g" | \
    sed "s/ZONE_COLOR_B/$COLOR_B/g")

# Save generated SDF to temp file
TMP_SDF="/tmp/${ZONE_ID}.sdf"
echo "$SDF_CONTENT" > "$TMP_SDF"

echo ""
echo "[1/1] Spawning zone in Gazebo..."

# Spawn model in Gazebo using gz service
# Note: We pass the file path to gz service
if gz service -s /world/default/create \
    --reqtype gz.msgs.EntityFactory \
    --reptype gz.msgs.Boolean \
    --timeout 5000 \
    --req "sdf_filename: \"$TMP_SDF\"" 2>&1 | grep -q "data: true"; then

    echo "✓ Zone spawned successfully in Gazebo"

    # Clean up temp SDF
    rm -f "$TMP_SDF"

    echo ""
    echo "=================================================="
    echo "  Zone $ZONE_ID Created Successfully!"
    echo "=================================================="
    echo "The ${ZONE_TYPE} zone '$ZONE_NAME' is now visible"
    echo "in Gazebo as a ${COLOR_R} ${COLOR_G} ${COLOR_B} cylinder."
    echo "=================================================="

    exit 0
else
    echo "✗ Failed to spawn zone in Gazebo"
    echo ""
    echo "Check that:"
    echo "  1. Gazebo simulation is running"
    echo "  2. 'gz service' command is available"
    echo "  3. World name is 'default'"

    # Clean up temp SDF
    rm -f "$TMP_SDF"

    exit 1
fi
