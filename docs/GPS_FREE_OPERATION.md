# GPS-Free Operation Guide

This guide explains how to operate drones without GPS, useful for:
- Indoor flight
- Simulation testing
- Drones without GPS hardware
- Development environments

## Overview

By default, PX4 requires a GPS fix before allowing arming. This is a safety feature for outdoor flights. However, for indoor operations or when using alternative positioning systems (vision-based, motion capture, etc.), you can configure PX4 to operate without GPS.

## Configuration

The project is configured to allow GPS-free operation through custom PX4 parameters loaded at startup.

### PX4 Parameters Set

The following parameters are automatically configured in `simulation/start_px4_sitl.sh`:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `COM_ARM_WO_GPS` | 1 | Allow arming without GPS fix |
| `EKF2_GPS_CTRL` | 0 | Disable GPS requirement for EKF2 estimator |
| `COM_PREARM_MODE` | 0 | Disable strict pre-arm checks |
| `NAV_RCL_ACT` | 0 | Disable RC loss failsafe action |
| `COM_RC_IN_MODE` | 1 | Allow operation without RC (for MAVROS control) |
| `COM_LOW_BAT_ACT` | 1 | Low battery: warning only (no auto-land) |
| `GF_ACTION` | 0 | Disable geofence |
| `COM_DISARM_LAND` | -1 | Never auto-disarm on land |
| `COM_POS_FS_EPH` | 10.0 | Relaxed position accuracy threshold |
| `COM_VEL_FS_EVH` | 2.0 | Relaxed velocity accuracy threshold |

## Flight Modes Without GPS

When operating without GPS, only certain flight modes are available:

### ✅ Available Modes
- **Manual** - Direct stick control (needs RC)
- **Stabilized** - Angle stabilization
- **Acro** - Rate control
- **Altitude** - Altitude hold (needs barometer)
- **Offboard** - External control via MAVROS

### ❌ Unavailable Modes (require GPS)
- **Position** - Position hold
- **Mission** - Waypoint navigation
- **Return** - Return to launch
- **Follow Me** - GPS-based tracking

## Safety Considerations

⚠️ **Important**: These settings reduce safety checks and should only be used in:
- Controlled environments (indoor, netted areas)
- Simulation
- Development/testing scenarios

### For Production Drones

For production indoor drones, consider implementing:

1. **Vision-Based Positioning**
   - Optical flow sensors
   - Depth cameras
   - SLAM systems

2. **Motion Capture Systems**
   - Vicon, OptiTrack, etc.
   - Provides absolute positioning

3. **Offboard Mode Control**
   - Full external control via MAVROS
   - Your software becomes the "brain"

## Offboard Mode (Recommended for Autonomous Operations)

For autonomous indoor flight, use Offboard mode:

```python
# ROS2 example - set Offboard mode
from mavros_msgs.srv import SetMode

set_mode_client.call_async(SetMode.Request(custom_mode='OFFBOARD'))
```

**Benefits**:
- Full control from external computer
- Bypass most PX4 safety checks
- Required for vision-based navigation
- Ideal for research and development

**Requirements**:
1. Send setpoint stream (position/velocity/attitude) at >2Hz
2. ARM command still required
3. PX4 monitors setpoint stream - if lost, will failsafe

## Testing in Simulation

The simulation is pre-configured for GPS-free operation. To test:

```bash
# Rebuild containers with new configuration
docker compose build simulation

# Start simulation
docker compose up simulation ros2_core mqtt backend frontend

# In another terminal, test arming
curl -X POST http://localhost:8000/drones/drone_1/arm
```

Expected result: ARM should succeed (or fail with a different error than GPS).

## Troubleshooting

### Still Can't Arm?

Check PX4 console for specific pre-arm errors:

```bash
docker exec -it artefac_simulation bash
# Inside container, PX4 console is accessible via pxh shell
# Look for "Preflight Fail" messages
```

Common issues:
- **Estimator not initialized**: Wait ~5 seconds after startup
- **Mode not set**: Set to STABILIZED or OFFBOARD
- **Attitude not converged**: Wait for IMU calibration

### Verify Parameters Were Set

```bash
docker logs artefac_simulation | grep "CUSTOM"
# Should see: "[CUSTOM] PX4 configured for GPS-free operation"
```

Or check parameters in PX4:

```bash
docker exec -it artefac_simulation bash
# In PX4 console (pxh):
param show COM_ARM_WO_GPS  # Should show: 1
```

## Alternative: Manual Parameter Setting

If you need to test different parameters without rebuilding:

```bash
# Access PX4 shell
docker exec -it artefac_simulation bash

# In PX4 console (pxh):
param set COM_ARM_WO_GPS 1
param save
```

## For Real Drones

When deploying to real hardware:

1. **QGroundControl**: Set parameters via GUI
2. **Parameter file**: Upload `simulation/config/px4_params_no_gps.params`
3. **Custom airframe**: Modify airframe config to include these params

⚠️ **Always test in a safe environment first!**

## References

- [PX4 Parameter Reference](https://docs.px4.io/main/en/advanced_config/parameter_reference.html)
- [PX4 Offboard Mode](https://docs.px4.io/main/en/flight_modes/offboard.html)
- [EKF2 Tuning](https://docs.px4.io/main/en/advanced_config/tuning_the_ecl_ekf.html)
