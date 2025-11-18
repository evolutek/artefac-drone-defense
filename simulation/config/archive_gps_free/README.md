# GPS-Free Configuration Archive

This folder contains **reference configurations** for running PX4 in GPS-free mode with vision-based localization.

## ⚠️ Important Notice

The project **currently operates in GPS-enabled mode**. These files are kept as reference for potential future development of indoor/GPS-denied operation capabilities.

## Archived Files

### `rcS_no_gps`
PX4 startup script with GPS-free parameters:
- `COM_ARM_WO_GPS=1` - Allow arming without GPS fix
- `EKF2_GPS_CTRL=0` - Disable GPS fusion in EKF2
- `EKF2_EV_CTRL=15` - Enable full vision fusion (position + velocity + yaw)
- `EKF2_HGT_REF=0` - Use barometer for height reference

### `px4_params_no_gps.params`
Minimal parameter file for GPS-free operation with essential settings.

## Usage (If Re-enabling GPS-Free Mode)

**Prerequisites:**
1. Vision bridge node must be active and publishing odometry
2. MAVROS vision plugin must forward vision data to PX4
3. `mavros_vision_config.yaml` must have `use_vision: true`

**Steps:**
1. Copy `rcS_no_gps` to PX4 build directory or use as parameter reference
2. Update `start_px4_sitl.sh` to inject GPS-free parameters instead of GPS-enabled
3. Set `use_vision: true` in `simulation/config/mavros_vision_config.yaml`
4. Ensure vision bridge node is enabled in `mqtt_bridge.launch.py`
5. Rebuild simulation container: `docker compose build simulation --no-cache`

## Architecture Notes

**GPS-Free Mode Requires:**
- Vision pose publisher → `/mavros/vision_pose/pose` topic
- EKF2 configured to fuse vision data instead of GPS
- Sufficient feature tracking in Gazebo environment

**Why GPS Mode Was Chosen:**
- Time constraints prevented full GPS-free debugging
- EKF2 convergence issues with vision fusion
- GPS mode provides reliable outdoor operation for MVP

## Related Documentation

- Current GPS configuration: See `../start_px4_sitl.sh` and `../rc.autostart.sh`
- Vision bridge code: `simulation/src/mqtt_bridge/mqtt_bridge/vision_pose_bridge.py`
- Original GPS-free docs: `docs/GPS_FREE_OPERATION.md` (if exists)

---

**Archived on:** 2025-11-18
**Reason:** Project migrated to GPS-enabled mode for reliable operation
**Status:** Reference only - not actively used
