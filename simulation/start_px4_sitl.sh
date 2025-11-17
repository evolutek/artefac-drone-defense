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

# Create extras.txt with MAVLink broadcast parameters (loaded BEFORE startup scripts)
log_step "Creating PX4 parameter file (extras.txt)"
mkdir -p /root/PX4-Autopilot/build/px4_sitl_default/etc
cat > /root/PX4-Autopilot/build/px4_sitl_default/etc/extras.txt << 'EXTRAS'
# MAVLink network broadcast parameters
MAV_0_BROADCAST 1
MAV_1_BROADCAST 1
# GPS-free arming parameters
COM_ARM_WO_GPS 1
EKF2_GPS_CTRL 0
COM_PREARM_MODE 0
NAV_RCL_ACT 0
COM_RC_IN_MODE 1
COM_LOW_BAT_ACT 1
GF_ACTION 0
COM_DISARM_LAND -1
COM_POS_FS_EPH 10.0
COM_VEL_FS_EVH 2.0
NAV_DLL_ACT 0
COM_DL_LOSS_T -1
# Vision fusion parameters
EKF2_EV_CTRL 15
EKF2_HGT_REF 3
EKF2_EV_DELAY 0
EKF2_EVP_NOISE 0.1
EKF2_EVV_NOISE 0.1
EKF2_EVA_NOISE 0.05
EXTRAS

# Build PX4 if rcS doesn't exist
if [ ! -f "/root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS" ]; then
    log_step "Building PX4 (first run)"
    if ! make px4_sitl_default 2>&1 | tee /tmp/px4_build.log | tail -20; then
        log_error "PX4 build failed! See /tmp/px4_build.log for details"
        tail -50 /tmp/px4_build.log
        exit 1
    fi
    log_info "PX4 build successful"
fi

# Backup and restore rcS to avoid double-patching
RCS_FILE="/root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS"
RCS_BACKUP="${RCS_FILE}.orig"

# Verify rcS exists
if [ ! -f "$RCS_FILE" ]; then
    log_error "rcS file not found at $RCS_FILE"
    log_error "This indicates PX4 build did not complete successfully"
    ls -la "$(dirname "$RCS_FILE")" || log_error "Directory does not exist"
    exit 1
fi

log_info "rcS file found at $RCS_FILE"

if [ ! -f "$RCS_BACKUP" ]; then
    log_step "Creating rcS backup"
    cp "$RCS_FILE" "$RCS_BACKUP"
else
    log_step "Restoring rcS from backup"
    cp "$RCS_BACKUP" "$RCS_FILE"
fi

# Patch rcS with GPS-free and vision fusion parameters
log_step "Patching rcS with GPS-free parameters"

# Check if the pattern exists in rcS
if ! grep -q '\. px4-rc\.mavlink' "$RCS_FILE"; then
    log_error "Pattern '. px4-rc.mavlink' not found in rcS"
    log_error "Cannot inject parameters. Showing rcS content:"
    head -30 "$RCS_FILE"
    exit 1
fi

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

# Verify the patch was applied
if grep -q "COM_ARM_WO_GPS" "$RCS_FILE"; then
    log_info "GPS-free parameters successfully injected into rcS"
else
    log_error "Failed to inject parameters into rcS"
    log_error "Showing rcS around mavlink line:"
    grep -A 5 -B 5 'px4-rc\.mavlink' "$RCS_FILE"
    exit 1
fi

# Remove cached parameters.bson to force PX4 to use rcS parameters
log_step "Removing cached parameters.bson (if exists)"
PARAMS_DIR="/root/PX4-Autopilot/build/px4_sitl_default/rootfs"
mkdir -p "$PARAMS_DIR"
if [ -f "$PARAMS_DIR/parameters.bson" ] || [ -f "$PARAMS_DIR/parameters_backup.bson" ]; then
    rm -f "$PARAMS_DIR/parameters.bson" "$PARAMS_DIR/parameters_backup.bson"
    log_info "Removed cached parameter files - PX4 will use rcS parameters"
else
    log_info "No cached parameter files found - first run"
fi

# Configure MAVLink for inter-container communication
log_step "Configuring MAVLink for MAVROS (multi-drone compatible)"
# Remove -x flag (localhost only) and add -p flag (enable broadcast) for network communication
# Keep variables for multi-drone support: udp_offboard_port_local = 14580+N, udp_offboard_port_remote = 14540+N
sed -i 's/mavlink start -x -u \$udp_offboard_port_local -r 4000000 -f -m onboard -o \$udp_offboard_port_remote/mavlink start -p -u $udp_offboard_port_local -r 4000000 -f -m onboard -o $udp_offboard_port_remote/g' /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.mavlink
# Also remove -x and add -p for GCS link
sed -i 's/mavlink start -x -u \$udp_gcs_port_local/mavlink start -p -u $udp_gcs_port_local/g' /root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.mavlink

# Configure MAVLink streams for MAVROS
log_step "Configuring MAVLink streams"

MAVLINK_FILE="/root/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/px4-rc.mavlink"
MAVLINK_BACKUP="${MAVLINK_FILE}.orig"

if [ ! -f "$MAVLINK_BACKUP" ]; then
    cp "$MAVLINK_FILE" "$MAVLINK_BACKUP"
fi

sed -i '/mavlink start -u \$udp_offboard_port_local.*-m onboard/a \
# MAVROS streams\
mavlink stream -r 5 -s SYS_STATUS -u $udp_offboard_port_local\
mavlink stream -r 5 -s EXTENDED_SYS_STATE -u $udp_offboard_port_local\
mavlink stream -r 5 -s BATTERY_STATUS -u $udp_offboard_port_local\
mavlink stream -r 5 -s TIMESYNC -u $udp_offboard_port_local\
mavlink stream -r 50 -s LOCAL_POSITION_NED -u $udp_offboard_port_local\
mavlink stream -r 30 -s GLOBAL_POSITION_INT -u $udp_offboard_port_local\
mavlink stream -r 10 -s ATTITUDE_QUATERNION -u $udp_offboard_port_local\
mavlink stream -r 10 -s ALTITUDE -u $udp_offboard_port_local\
mavlink stream -r 10 -s ATTITUDE -u $udp_offboard_port_local\
mavlink stream -r 5 -s RC_CHANNELS -u $udp_offboard_port_local\
' "$MAVLINK_FILE"

# Launch PX4 SITL
log_info "Configuration complete"
echo -e "\n${BLUE}=== Launching PX4 SITL ===${NC}"
echo -e "${BLUE}Command:${NC} make px4_sitl ${PX4_SIM_MODEL}\n"

exec make px4_sitl ${PX4_SIM_MODEL}
