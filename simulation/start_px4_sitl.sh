#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${GREEN}[PX4] ✓${NC} $1"; }
log_step() { echo -e "${BLUE}[PX4] →${NC} $1"; }
log_warn() { echo -e "${YELLOW}[PX4] ⚠${NC} $1"; }
log_error() { echo -e "${RED}[PX4] ✗${NC} $1"; }

echo -e "\n${BLUE}=== PX4 SITL + Gazebo Harmonic ===${NC}\n"

# Source ROS2
source /opt/ros/humble/setup.bash

# Display configuration
log_step "Configuration"
echo "  Display:       ${DISPLAY:-not set}"
echo "  Headless:      ${HEADLESS}"
echo "  Model:         ${PX4_SIM_MODEL}"
echo "  World:         ${PX4_GZ_WORLD}"
echo "  Home:          ${PX4_HOME_LAT},${PX4_HOME_LON} (${PX4_HOME_ALT}m)"

# Setup X11 for GUI mode
if [ "$HEADLESS" = "0" ]; then
    if [ -n "$DISPLAY" ]; then
        if [ -n "$XAUTHORITY" ] && [ -f "$XAUTHORITY" ]; then
            chmod 644 "$XAUTHORITY" 2>/dev/null || true
            log_info "GUI mode - X11 configured"
        else
            log_warn "XAUTHORITY not found - GUI may not work"
        fi
        xhost +local:docker 2>/dev/null || true
    else
        log_warn "DISPLAY not set - GUI will not work"
    fi
else
    log_info "Headless mode - no GUI"
fi

# Ensure log directory exists
mkdir -p /root/.ros/log

# Create gz wrapper to handle GUI/headless mode
log_step "Creating Gazebo wrapper"
cat > /usr/local/bin/gz << 'GZWRAPPER'
#!/bin/bash
# Wrapper for gz command - removes -s flag in GUI mode
if [ "$1" = "sim" ] && [ "$HEADLESS" = "0" ]; then
    args=()
    for arg in "$@"; do
        [ "$arg" != "-s" ] && args+=("$arg")
    done
    exec /usr/bin/gz "${args[@]}"
else
    exec /usr/bin/gz "$@"
fi
GZWRAPPER
chmod +x /usr/local/bin/gz
export PATH="/usr/local/bin:$PATH"

# PX4 environment setup
cd /root/PX4-Autopilot
export PX4_GZ_WORLD=${PX4_GZ_WORLD:-default}
export PX4_SIM_MODEL=${PX4_SIM_MODEL:-gz_x500}
export PX4_SYS_AUTOSTART=4001
export PX4_SIM_SPEED_FACTOR=1

# Prepare PX4 build directory
log_step "Preparing PX4 configuration"
mkdir -p /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix

# Build PX4 if rcS doesn't exist
if [ ! -f "/root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS" ]; then
    log_step "Building PX4 (first run)"
    make px4_sitl_default > /dev/null 2>&1
fi

# Backup and restore rcS to avoid double-patching
RCS_FILE="/root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS"
RCS_BACKUP="${RCS_FILE}.orig"

if [ ! -f "$RCS_BACKUP" ]; then
    cp "$RCS_FILE" "$RCS_BACKUP"
else
    cp "$RCS_BACKUP" "$RCS_FILE"
fi

# Patch rcS with GPS-free and vision fusion parameters
log_step "Patching rcS with GPS-free parameters"
sed -i '/\. px4-rc\.mavlink/i \
# GPS-free and vision fusion parameters\
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
param set NAV_DLL_ACT 0\
param set COM_DL_LOSS_T -1\
param set MAV_0_BROADCAST 1\
param set MAV_1_BROADCAST 1\
param set EKF2_EV_CTRL 15\
param set EKF2_HGT_REF 3\
param set EKF2_EV_DELAY 0\
param set EKF2_EVP_NOISE 0.1\
param set EKF2_EVV_NOISE 0.1\
param set EKF2_EVA_NOISE 0.05\
' "$RCS_FILE"

# Enable MAVLink network broadcast and change mode to accept all message types
log_step "Enabling MAVLink broadcast and setting normal mode"
sed -i 's/mavlink start -x /mavlink start /g' /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.mavlink
# Change onboard mode to normal mode to accept commands from MAVROS
sed -i 's/-m onboard/-m normal/g' /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.mavlink

# Configure MAVLink streams for MAVROS
log_step "Configuring MAVLink streams"

MAVLINK_FILE="/root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.mavlink"
MAVLINK_BACKUP="${MAVLINK_FILE}.orig"

if [ ! -f "$MAVLINK_BACKUP" ]; then
    cp "$MAVLINK_FILE" "$MAVLINK_BACKUP"
fi

sed -i '/mavlink start -u \$udp_offboard_port_local.*-m onboard/a \
# MAVROS streams\
mavlink stream -r 50 -s LOCAL_POSITION_NED -u $udp_offboard_port_local\
mavlink stream -r 30 -s GLOBAL_POSITION_INT -u $udp_offboard_port_local\
mavlink stream -r 10 -s ATTITUDE_QUATERNION -u $udp_offboard_port_local\
mavlink stream -r 10 -s ALTITUDE -u $udp_offboard_port_local\
' "$MAVLINK_FILE"

# Launch PX4 SITL
log_info "Configuration complete"
echo -e "\n${BLUE}=== Launching PX4 SITL ===${NC}"
echo -e "${BLUE}Command:${NC} make px4_sitl ${PX4_SIM_MODEL}\n"

exec make px4_sitl ${PX4_SIM_MODEL}
