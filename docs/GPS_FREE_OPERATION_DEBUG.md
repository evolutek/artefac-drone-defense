# GPS-Free Operation - Debug History

**Date**: 2025-11-10
**Status**: 🔧 IN PROGRESS - Vision bridge working, investigating MAVROS→PX4 forwarding

> **Note**: For current documentation, see [GPS_FREE_OPERATION.md](GPS_FREE_OPERATION.md) and [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
> This file contains the historical debug process and is kept for reference only.

---

## Executive Summary

**Problem**: Drone refused to arm due to "ekf2 missing data" error
**Root Cause**: Multiple issues in the vision-based positioning pipeline
**Solution**: Direct Gazebo Transport integration + MAVROS namespace fix + vision fusion configuration

**Timeline**:
- Initial issue: PX4 refused arming (no GPS, no vision data)
- Phase 1: Fixed EKF2 configuration for vision fusion
- Phase 2: Fixed MAVROS service namespace issues
- Phase 3: Implemented Gazebo Transport Python bridge (vision data @ 50 Hz ✓)
- **Phase 4 (CURRENT)**: Investigating MAVROS vision_pose plugin MAVLink forwarding

---

## Phase 1: EKF2 Configuration

**Problem**: PX4 refused to arm with "Preflight Fail: ekf2 missing data"
**Cause**: EKF2 had no position source (no GPS, no vision data)

**Solution**: Added vision fusion parameters to `simulation/start_px4_sitl.sh`

**Key Parameters:**
- `EKF2_EV_CTRL = 15` - Enable vision fusion (position, velocity, yaw)
- `EKF2_HGT_REF = 3` - Use vision as height reference
- `EKF2_EVP_NOISE = 0.1` - Vision position noise
- `COM_ARM_WO_GPS = 1` - Allow arming without GPS

**Result**: ✅ EKF2 configured to accept vision data

---

## Phase 2: MAVROS Service Namespace Issue

**Problem**: MAVROS services existed but never responded (infinite timeout)
**Symptoms**:
- `ros2 service call /mavros_node/arming` - no response
- Backend ARM command timed out after 5 seconds

**Root Cause**: MAVROS launched with `namespace:=mavros`, creating:
- Functional services at `/mavros/mavros_node/arming`
- "Ghost" non-functional services at `/mavros_node/arming`

The mqtt_bridge looked for `/mavros_node/arming` which appeared in the service list but never responded.

**Solution**: Removed namespace parameter in `docker-compose.yml`

```diff
- ros2 launch mavros_launcher px4_sitl.launch.py ... namespace:=mavros &
+ ros2 launch mavros_launcher px4_sitl.launch.py ... &
```

**Additional Fix**: Added active wait for MAVROS services before starting mqtt_bridge

```bash
until ros2 service list | grep -q 'mavros_node/arming'; do
  echo 'Waiting for MAVROS services...'
  sleep 2
done
```

**Result**: ✅ Services now respond within <1 second

---

## Phase 3: Vision Pose Bridge (Final Solution)

**Problem**: `ros_gz_bridge` couldn't convert Gazebo message types
**Error**: "Unknown message type [8] [9]" - no direct mapping from `gz.msgs.Pose_V` to ROS2

**Attempted Solutions**:
1. ❌ Use ros_gz_bridge with different topic mappings - failed (no direct type mapping)
2. ❌ Static test data (0,0,0) at 30 Hz - worked for testing but not production
3. ✅ **Direct Gazebo Transport Python API** - final solution

**Implementation**: Rewrote `vision_pose_bridge.py` to use `gz.transport13` Python library

**Key Changes**:
- Added Gazebo Transport dependencies to Dockerfile: `python3-gz-transport13`, `libgz-transport13-dev`
- Subscribe directly to `/world/default/dynamic_pose/info` (gz.msgs.Pose_V)
- Filter by `model_name` to extract specific drone pose
- Convert Gazebo pose → ROS2 `geometry_msgs/PoseStamped`
- Publish to `/mavros/vision_pose/pose` at 52 Hz

**Architecture**:
```python
# Gazebo Transport Node
gz_node = GzNode()
gz_node.subscribe(Pose_V, '/world/default/dynamic_pose/info', callback)

# In callback: filter by model_name and convert
for pose in msg.pose:
    if pose.name == model_name:  # e.g., 'x500_0'
        vision_msg = PoseStamped()
        vision_msg.pose.position = pose.position
        # ... convert quaternion, set frame_id, timestamp
        publisher.publish(vision_msg)  # → /mavros/vision_pose/pose
```

**Results**:
- ✅ Real Gazebo data at 52 Hz (vs 30 Hz static test data)
- ✅ Scalable architecture (one bridge per drone, O(1) performance)
- ✅ No dependency on ros_gz_bridge
- ✅ Production-ready

**Modified Files**:
- `simulation/Dockerfile` - Added `python3-gz-transport13`
- `simulation/src/mqtt_bridge/mqtt_bridge/vision_pose_bridge.py` - Complete rewrite (187 lines)
- `simulation/src/mqtt_bridge/launch/mqtt_bridge.launch.py` - Removed ros_gz_bridge
- `docker-compose.yml` - Fixed MAVROS namespace, added service wait

---

## Verification Commands

**Check vision bridge is publishing:**
```bash
docker logs artefac_ros2_integration 2>&1 | grep vision_pose_bridge | tail -5
# Expected: [INFO] Vision pose published: pos=[x, y, z] (52 msgs/sec)
```

**Verify MAVROS receives data:**
```bash
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic hz /mavros/vision_pose/pose"
# Expected: average rate: ~52 Hz
```

**Compare with Gazebo ground truth:**
```bash
docker exec artefac_simulation gz model -m x500_0 -p
# Should match vision bridge output
```

---

## Summary

**Final Architecture**:
```
Gazebo Harmonic
    ↓ /world/default/dynamic_pose/info (gz.msgs.Pose_V @ 50Hz)
vision_pose_bridge (Gazebo Transport Python)
    ↓ Filters by model_name, converts to ROS2
    ↓ /mavros/vision_pose/pose (geometry_msgs/PoseStamped @ 52Hz)
MAVROS
    ↓ MAVLink: VISION_POSITION_ESTIMATE
PX4 EKF2
    ↓ Fuses IMU + vision data
Local Position Estimate
```

---

## Phase 4: MAVROS Vision Pose Forwarding (CURRENT INVESTIGATION)

**Problem**: PX4 still reports "ekf2 missing data" despite vision bridge publishing @ 50 Hz
**Status**: 🔧 Investigating whether MAVROS forwards vision data to PX4 via MAVLink

**What's Working** ✅:
1. Vision Pose Bridge: Publishing real Gazebo data @ 50 Hz to `/mavros/vision_pose/pose`
2. MAVROS `vision_pose` plugin: Loaded and initialized
3. PX4 EKF2 parameters: Configured for vision fusion (`EKF2_EV_CTRL=15`, `EKF2_HGT_REF=3`)

**Current Investigation** 🔍:
- **Discovery**: MAVROS ROS2 Humble **does NOT have `use_vision` parameter** anymore
- The `global_position.use_vision` parameter does not exist in this version
- Vision pose forwarding should happen **automatically** when publishing to `/mavros/vision_pose/pose`
- **Hypothesis**: MAVROS may not be sending `VISION_POSITION_ESTIMATE` MAVLink messages to PX4

**Next Steps**:
1. ✅ Verify MAVROS is connected to PX4 (check `/mavros/state`)
2. Monitor MAVLink traffic to confirm `VISION_POSITION_ESTIMATE` messages
3. Check PX4 logs for vision message reception
4. Investigate MAVROS vision_pose plugin source code if necessary

**Debug Commands**:
```bash
# Check MAVROS state
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic echo /mavros/state --once"

# Monitor vision pose topic
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic hz /mavros/vision_pose/pose"

# Check PX4 for vision messages
docker logs --since 2m artefac_simulation 2>&1 | grep -i "vision_position\|mocap"

# Verify EKF2 status
docker logs artefac_simulation 2>&1 | grep -i "ekf2.*vision"
```

**Status**: 🔧 **Investigation in progress**

**For current usage**, see:
- [GPS_FREE_OPERATION.md](GPS_FREE_OPERATION.md) - Configuration and usage guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Debugging commands and procedures
- [COMMUNICATION_FLOW.md](COMMUNICATION_FLOW.md) - System architecture and terminology

---

**Last Updated**: 2025-11-10 10:30 UTC
**Document Status**: Active debugging session
