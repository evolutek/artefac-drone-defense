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

# GPS-free parameters and MAVLink broadcast configured via environment
echo "==================================================="
echo "Configuring GPS-free parameters by patching rcS"
echo "==================================================="

# Set PX4 parameters via environment variables (applied at runtime)
export PX4_SYS_AUTOSTART=4001  # Generic quadcopter
export PX4_SIM_SPEED_FACTOR=1

# Patch the rcS file in the build directory to include our custom parameters
# This ensures they are executed during PX4 startup
mkdir -p /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix

# Wait for rcS to exist (it's created during make)
if [ ! -f "/root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS" ]; then
    echo "Building PX4 first to generate rcS..."
    cd /root/PX4-Autopilot
    make px4_sitl_default
fi

# Backup original rcS and restore if already patched
if [ ! -f "/root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS.orig" ]; then
    cp /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS \
       /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS.orig
else
    # Restore from backup to avoid double-patching
    cp /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS.orig \
       /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS
fi

# Inject our parameters right before px4-rc.mavlink is sourced
# This ensures MAVLink broadcast parameters are set BEFORE MAVLink instances are created
sed -i '/\. px4-rc\.mavlink/i \
# Custom GPS-free parameters and MAVLink broadcast\
param set COM_ARM_WO_GPS 1\
param set EKF2_GPS_CTRL 0\
param set COM_PREARM_MODE 0\
param set NAV_RCL_ACT 0\
param set COM_RC_IN_MODE 1\
param set COM_LOW_BAT_ACT 1\
param set GF_ACTION 0\
param set COM_DISARM_LAND -1\
param set COM_POS_FS_EPH 10.0\
param set COM_VEL_FS_EVH 2.0\
param set MAV_0_BROADCAST 1\
param set MAV_1_BROADCAST 1\
echo "[CUSTOM] PX4 configured for GPS-free operation with MAVLink broadcast"\
' /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS

echo "rcS patched with GPS-free parameters"

# Remove -x flag from mavlink start commands in px4-rc.mavlink to enable network broadcasting
# The -x flag forces localhost-only mode and ignores MAV_*_BROADCAST parameters
sed -i 's/mavlink start -x /mavlink start /g' /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.mavlink

echo "px4-rc.mavlink patched to remove localhost-only flag"

# Add MAVLink stream configuration for MAVROS offboard connection
# The offboard instance (port 14580) needs explicit streams for position data
echo "==================================================="
echo "Configuring MAVLink streams for MAVROS"
echo "==================================================="

# Backup original px4-rc.mavlink if not already backed up
if [ ! -f "/root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.mavlink.orig" ]; then
    cp /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.mavlink \
       /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.mavlink.orig
fi

# Add stream commands after the offboard MAVLink instance start
# These commands configure what messages are sent to MAVROS
sed -i '/mavlink start -u \$udp_offboard_port_local.*-m onboard/a \
# Stream position and attitude data to MAVROS at appropriate rates\
mavlink stream -r 50 -s LOCAL_POSITION_NED -u $udp_offboard_port_local\
mavlink stream -r 30 -s GLOBAL_POSITION_INT -u $udp_offboard_port_local\
mavlink stream -r 10 -s ATTITUDE_QUATERNION -u $udp_offboard_port_local\
mavlink stream -r 10 -s ALTITUDE -u $udp_offboard_port_local\
echo "[CUSTOM] MAVLink streams configured for MAVROS offboard connection"\
' /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.mavlink

echo "MAVLink streams configured for position data"

# Launch PX4 SITL with Gazebo
echo "==================================================="
echo "Launching PX4 SITL..."
echo "Command: make px4_sitl ${PX4_SIM_MODEL}"
echo "==================================================="

# Execute make command - this will start both PX4 and Gazebo
exec make px4_sitl ${PX4_SIM_MODEL}
