#!/bin/sh
# Custom PX4 parameters for GPS-enabled operation and MAVLink broadcast
# This file is sourced during PX4 startup

# Require GPS fix for arming
param set COM_ARM_WO_GPS 0

# Enable GPS fusion for EKF2 (horizontal + vertical)
param set EKF2_GPS_CTRL 7

# Disable pre-arm mode (allows arming in more situations)
param set COM_PREARM_MODE 0

# RC loss action: disabled
param set NAV_RCL_ACT 0

# Allow arming without RC (for MAVROS control)
param set COM_RC_IN_MODE 1

# Low battery action: warning only
param set COM_LOW_BAT_ACT 1

# Geofence action: none
param set GF_ACTION 0

# Don't auto-disarm on land (-1 = never)
param set COM_DISARM_LAND -1

# Reduce position/velocity checks for pre-arm
param set COM_POS_FS_EPH 10.0
param set COM_VEL_FS_EVH 2.0

# Enable MAVLink broadcast (fixes MAVROS connection)
param set MAV_0_BROADCAST 1
param set MAV_1_BROADCAST 1

echo "[CUSTOM] PX4 configured for GPS-enabled operation with MAVLink broadcast"