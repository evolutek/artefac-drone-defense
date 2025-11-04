#!/bin/bash
set -e

echo "==================================================="
echo "Starting PX4 SITL with Gazebo Harmonic"
echo "==================================================="

# Source ROS2 environment
source /opt/ros/humble/setup.bash

# Display configuration
echo "Display: $DISPLAY"
echo "XAUTHORITY: $XAUTHORITY"
echo "Headless mode: $HEADLESS"
echo "PX4 Model: $PX4_SIM_MODEL"
echo "PX4 World: $PX4_GZ_WORLD"
echo "Home position: $PX4_HOME_LAT,$PX4_HOME_LON (alt: ${PX4_HOME_ALT}m)"
echo "---------------------------------------------------"

# Setup X11 permissions for GUI if not headless
if [ "$HEADLESS" = "0" ]; then
    echo "GUI mode enabled - configuring X11..."
    if [ -n "$DISPLAY" ]; then
        # Try to setup xauth if available
        if [ -f "$XAUTHORITY" ]; then
            echo "Using XAUTHORITY: $XAUTHORITY"
        else
            echo "Warning: XAUTHORITY file not found, GUI may not work"
        fi

        # Allow X11 connections (fallback)
        xhost +local:docker 2>/dev/null || echo "Note: xhost command not available"
    else
        echo "Warning: DISPLAY not set, GUI will not work"
    fi
else
    echo "Headless mode - no GUI will be displayed"
fi

# Ensure log directory exists
mkdir -p /root/.ros/log

# Create gz wrapper script that handles HEADLESS flag
cat > /usr/local/bin/gz << 'GZWRAPPER'
#!/bin/bash
# Wrapper for gz command that removes -s flag if HEADLESS=0

if [ "$1" = "sim" ] && [ "$HEADLESS" = "0" ]; then
    # Remove -s flag from arguments if present
    args=()
    skip_next=false
    for arg in "$@"; do
        if [ "$skip_next" = true ]; then
            skip_next=false
            continue
        fi
        if [ "$arg" = "-s" ]; then
            echo "[GZ WRAPPER] Removing -s flag (GUI mode enabled)"
            continue
        fi
        args+=("$arg")
    done
    exec /usr/bin/gz "${args[@]}"
else
    # Pass through all arguments unchanged
    exec /usr/bin/gz "$@"
fi
GZWRAPPER

chmod +x /usr/local/bin/gz

# Make sure /usr/local/bin is before /usr/bin in PATH
export PATH="/usr/local/bin:$PATH"

# Build PX4 arguments based on environment
cd /root/PX4-Autopilot

# Export PX4 environment variables
export PX4_GZ_WORLD=${PX4_GZ_WORLD:-default}
export PX4_SIM_MODEL=${PX4_SIM_MODEL:-gz_x500}

# Launch PX4 SITL with Gazebo
echo "Launching PX4 SITL..."
echo "Command: make px4_sitl ${PX4_SIM_MODEL}"

# Execute make command - this will start both PX4 and Gazebo
exec make px4_sitl ${PX4_SIM_MODEL}
