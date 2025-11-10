# GPS-Free Operation Guide

This guide explains how to operate drones without GPS, useful for:
- Indoor flight
- Simulation testing
- Drones without GPS hardware
- Development environments

## Overview

By default, PX4 requires a GPS fix before allowing arming. This is a safety feature for outdoor flights. However, for indoor operations or when using alternative positioning systems (vision-based, motion capture, etc.), you can configure PX4 to operate without GPS.

## Configuration

The project is configured to operate without GPS using vision-based positioning from Gazebo simulation.

### Vision-Based Positioning Architecture

```
Gazebo Harmonic (simulation)
    ↓ /world/default/dynamic_pose/info (gz.msgs.Pose_V @ 50Hz)
vision_pose_bridge (Gazebo Transport Python)
    ↓ Filters by model_name, converts to ROS2
    ↓ /mavros/vision_pose/pose (geometry_msgs/PoseStamped @ 52Hz)
MAVROS (ROS2 → MAVLink)
    ↓ MAVLink: VISION_POSITION_ESTIMATE
PX4 EKF2
    ↓ Fuses IMU + vision data
Local Position Estimate
```

**Key Features:**
- ✅ Direct Gazebo Transport Python API (no ros_gz_bridge needed)
- ✅ Real-time pose data at 52 Hz
- ✅ Per-drone filtering (scalable to multiple drones)
- ✅ Production-ready architecture

### PX4 Parameters Set

The following parameters are automatically configured in `simulation/start_px4_sitl.sh`:

**Basic GPS-Free Parameters:**
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

**Vision Fusion Parameters:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `EKF2_EV_CTRL` | 15 | Enable position, velocity, yaw fusion from vision |
| `EKF2_HGT_REF` | 3 | Use vision as height reference |
| `EKF2_EV_DELAY` | 0 | Vision data delay (0ms for simulation) |
| `EKF2_EVP_NOISE` | 0.1 | Vision position measurement noise (m) |
| `EKF2_EVV_NOISE` | 0.1 | Vision velocity measurement noise (m/s) |
| `EKF2_EVA_NOISE` | 0.05 | Vision angle measurement noise (rad) |

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

The simulation is pre-configured for GPS-free operation with real-time vision data. To test:

```bash
# Start all services
docker compose up -d

# Wait for containers to initialize (~10 seconds)
sleep 10

# Test arming
curl -X POST http://localhost:8000/drones/drone_1/arm
```

Expected result: ARM command executes successfully (check backend logs for PX4 response).

### Verification Commands

**Check vision pose bridge is publishing:**
```bash
docker logs artefac_ros2_integration 2>&1 | grep vision_pose_bridge | tail -5
# Expected: [INFO] Vision pose published: pos=[x, y, z] (52 msgs/sec)
```

**Verify MAVROS receives vision data:**
```bash
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic hz /mavros/vision_pose/pose"
# Expected: average rate: ~52 Hz
```

**Compare with Gazebo ground truth:**
```bash
docker exec artefac_simulation gz model -m x500_0 -p
# Should match vision bridge output
```

### Multi-Drone Configuration

The vision pose bridge is designed for scalability:

```yaml
# Example: Launch 3 drones (in docker-compose.yml)
ros2 launch mqtt_bridge mqtt_bridge.launch.py drone_id:=drone_1 model_name:=x500_0 &
ros2 launch mqtt_bridge mqtt_bridge.launch.py drone_id:=drone_2 model_name:=x500_1 &
ros2 launch mqtt_bridge mqtt_bridge.launch.py drone_id:=drone_3 model_name:=x500_2 &
```

**Benefits:**
- Each bridge filters its own drone from the shared Gazebo topic
- Parallel execution (one process per drone)
- Crash isolation (one bridge failure doesn't affect others)
- O(1) performance per drone

## Troubleshooting

For detailed troubleshooting commands and procedures, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Quick Checks

**Verify vision pose bridge is working:**
```bash
docker logs artefac_ros2_integration | grep "Vision pose published"
# Should show regular updates at ~52 Hz
```

**Check PX4 EKF2 status:**
```bash
docker logs artefac_simulation | grep -i "ekf2"
```

**Verify parameters were applied:**
```bash
docker logs artefac_simulation | grep "COM_ARM_WO_GPS"
# Expected: COM_ARM_WO_GPS: curr: 0 -> new: 1
```

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Vision bridge not publishing | No "Vision pose published" in logs | Rebuild ROS2 container: `docker compose build ros2_integration` |
| EKF2 missing data | "Preflight Fail: ekf2 missing data" | Wait 10 seconds for initialization, check vision bridge |
| Wrong flight mode | ARM rejected | Set to MANUAL, STABILIZED, or OFFBOARD |
| Services not responding | Timeout on ARM command | Check MAVROS connection: `ros2 topic echo /mavros/state --once` |

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
