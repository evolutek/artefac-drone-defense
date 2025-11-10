# Troubleshooting Guide - Artefac Drone Defense

This document provides debugging commands and procedures for diagnosing issues across all system components.

## Quick Diagnostics

### System Health Check

```bash
# Check all containers are running
docker compose ps

# Check logs for errors (last 50 lines per service)
docker compose logs --tail 50 backend
docker compose logs --tail 50 ros2_integration
docker compose logs --tail 50 simulation
docker compose logs --tail 50 mqtt
```

---

## Component-Specific Diagnostics

### MAVROS Connection

**Check MAVROS is connected to PX4:**
```bash
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic echo /mavros/state --once"
# Expected: connected: true
```

**List all MAVROS services:**
```bash
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 service list | grep mavros"
# Should show: /mavros_node/arming, /mavros_node/set_mode, /mavros_node/cmd/takeoff, etc.
```

**Test arming service directly:**
```bash
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 service call /mavros_node/arming mavros_msgs/srv/CommandBool '{value: true}'"
# Response: success=true/false, result=<code>
```

---

### MQTT Bridge

**Check MQTT bridge is receiving commands:**
```bash
docker compose logs ros2_integration | grep "Received command"
```

**Monitor all MQTT topics:**
```bash
docker exec artefac_mqtt mosquitto_sub -t "drone/#" -v
```

**Publish test command:**
```bash
docker exec artefac_mqtt mosquitto_pub -t "drone/drone_1/command" -m '{"command":"ARM","timestamp":1234567890}'
```

**Check MQTT broker statistics:**
```bash
docker exec artefac_mqtt mosquitto_sub -t '$SYS/broker/messages/received' -C 1
docker exec artefac_mqtt mosquitto_sub -t '$SYS/broker/clients/connected' -C 1
```

---

### PX4 SITL

**Check PX4 is running:**
```bash
docker exec artefac_simulation ps aux | grep px4
```

**View PX4 parameters:**
```bash
docker logs artefac_simulation | grep "param set"
```

**Check for pre-flight errors:**
```bash
docker logs artefac_simulation | grep -i "preflight"
```

**Check EKF2 status:**
```bash
docker logs artefac_simulation | grep -i "ekf2"
```

**Test arming directly in PX4:**
```bash
docker exec artefac_simulation /root/PX4-Autopilot/build/px4_sitl_default/bin/px4-commander arm
```

**Check PX4 commander status:**
```bash
docker exec artefac_simulation /root/PX4-Autopilot/build/px4_sitl_default/bin/px4-commander status
```

---

### ROS2 Topics and Nodes

**List all ROS2 nodes:**
```bash
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 node list"
# Expected: /mavros_node, /mqtt_bridge, /vision_pose_bridge
```

**List all ROS2 topics:**
```bash
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic list"
```

**Check topic frequency:**
```bash
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic hz /mavros/vision_pose/pose"
# Expected: ~50 Hz
```

**Check topic bandwidth:**
```bash
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic bw /mavros/local_position/pose"
```

**Echo a topic (single message):**
```bash
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic echo /mavros/local_position/pose --once"
```

---

### Vision Pose Bridge (GPS-Free Operation)

**Check vision pose bridge is publishing:**
```bash
docker logs artefac_ros2_integration 2>&1 | grep vision_pose_bridge | tail -10
# Expected: [INFO] Vision pose published: pos=[x, y, z] (XX msgs/sec)
```

**Verify vision data reaches MAVROS:**
```bash
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic echo /mavros/vision_pose/pose --once"
# Expected: Real pose data from Gazebo
```

**Check Gazebo model pose:**
```bash
docker exec artefac_simulation gz model -m x500_0 -p
# Compare with vision bridge output
```

---

### Gazebo Simulation

**List Gazebo topics:**
```bash
docker exec artefac_simulation gz topic -l
```

**Echo Gazebo pose topic:**
```bash
docker exec artefac_simulation gz topic -e -t /world/default/dynamic_pose/info -n 1
```

**Check Gazebo models:**
```bash
docker exec artefac_simulation gz model -l
# Expected: x500_0, ground_plane
```

---

## Common Issues and Solutions

### Issue: ARM command times out

**Symptoms:**
- Backend returns 504 Gateway Timeout
- Frontend shows "Timeout waiting for drone response"

**Diagnosis:**
```bash
# 1. Check MQTT broker is running
docker compose ps mqtt

# 2. Check ROS2 bridge is running
docker compose ps ros2_integration

# 3. Check MQTT bridge logs
docker compose logs ros2_integration | grep -i "error\|warn"
```

**Solutions:**
- Restart ROS2 integration container: `docker compose restart ros2_integration`
- Check MQTT broker connection: `docker compose logs mqtt`
- Verify MAVROS services are available (see MAVROS Connection section)

---

### Issue: PX4 rejects ARM command

**Symptoms:**
- Backend returns 400 Bad Request
- Message: "PX4 rejected command (check GPS fix, flight mode, or safety checks)"

**Diagnosis:**
```bash
# Check PX4 pre-flight errors
docker logs artefac_simulation | grep -i "preflight\|arm"

# Check if GPS-free params are set
docker logs artefac_simulation | grep "COM_ARM_WO_GPS"
# Expected: COM_ARM_WO_GPS: curr: 0 -> new: 1

# Check EKF2 status
docker logs artefac_simulation | grep -i "ekf2"
```

**Solutions:**
- Ensure GPS-free parameters are configured (see `GPS_FREE_OPERATION.md`)
- Wait 5-10 seconds after container start for EKF2 to initialize
- Check vision pose bridge is publishing data (see Vision Pose Bridge section)
- Verify flight mode is compatible (MANUAL, STABILIZED, or OFFBOARD)

---

### Issue: Vision pose bridge not publishing

**Symptoms:**
- No "Vision pose published" in logs
- EKF2 reports "missing data"

**Diagnosis:**
```bash
# Check vision_pose_bridge node is running
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 node list | grep vision"

# Check for errors in logs
docker compose logs ros2_integration | grep -i "vision\|error"

# Verify Gazebo Transport library is installed
docker exec artefac_ros2_integration dpkg -l | grep gz-transport
# Expected: python3-gz-transport13
```

**Solutions:**
- Rebuild ROS2 integration container: `docker compose build --no-cache ros2_integration && docker compose up -d ros2_integration`
- Check Gazebo simulation is publishing poses (see Gazebo Simulation section)
- Verify model name matches Gazebo model: `gz model -l` should show `x500_0`

---

### Issue: Frontend shows "MQTT broker not available"

**Symptoms:**
- Backend returns 503 Service Unavailable
- Cannot send any commands

**Diagnosis:**
```bash
# Check MQTT broker is running
docker compose ps mqtt

# Check backend can connect
docker compose logs backend | grep -i "mqtt"
```

**Solutions:**
- Start MQTT broker: `docker compose up -d mqtt`
- Restart backend: `docker compose restart backend`
- Check MQTT broker configuration in `.env` file

---

### Issue: ROS2 nodes not discovered

**Symptoms:**
- `ros2 node list` shows incomplete list
- Services not available

**Diagnosis:**
```bash
# Check ROS_DOMAIN_ID matches across containers
docker compose exec ros2_integration bash -c "echo \$ROS_DOMAIN_ID"
docker compose exec simulation bash -c "echo \$ROS_DOMAIN_ID"
# Both should show: 42

# Check ROS2 daemon
docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 daemon stop && ros2 daemon start"
```

**Solutions:**
- Ensure all containers use `network_mode: host` in `docker-compose.yml`
- Restart containers: `docker compose restart ros2_integration simulation`
- Clear ROS2 daemon: `ros2 daemon stop` (inside container)

---

## Performance Monitoring

### Check Command Latency

**Measure end-to-end ARM latency:**
```bash
time curl -X POST http://localhost:8000/drones/drone_1/arm
# Expected: < 1 second
```

### Monitor Telemetry Rate

**Check backend telemetry publishing:**
```bash
docker compose logs backend | grep "Forwarding telemetry" | tail -20
# Should show regular updates (~2 Hz)
```

**Check MQTT telemetry rate:**
```bash
docker exec artefac_mqtt mosquitto_sub -t "drone/+/telemetry" -v | ts
# Shows timestamps for each message
```

---

## Log Analysis Tips

### Filter by severity
```bash
docker compose logs ros2_integration | grep -E "\[ERROR\]|\[WARN\]"
```

### Follow logs in real-time
```bash
docker compose logs -f ros2_integration
```

### Get logs between timestamps
```bash
docker compose logs --since "2025-11-10T00:00:00" --until "2025-11-10T01:00:00" ros2_integration
```

### Search for specific pattern
```bash
docker compose logs ros2_integration | grep -C 3 "arm"
# Shows 3 lines before and after each match
```

---

## Testing Checklist

Before reporting an issue, verify:

- [ ] All containers are running: `docker compose ps`
- [ ] MAVROS connected: `ros2 topic echo /mavros/state --once`
- [ ] MQTT broker reachable: `mosquitto_sub -t "drone/#" -v`
- [ ] Vision bridge publishing: Check logs for "Vision pose published"
- [ ] PX4 GPS-free params set: `docker logs artefac_simulation | grep COM_ARM_WO_GPS`
- [ ] No errors in logs: `docker compose logs | grep -i error`

---

## Related Documentation

- [COMMUNICATION_FLOW.md](COMMUNICATION_FLOW.md) - System architecture and message flows
- [GPS_FREE_OPERATION.md](GPS_FREE_OPERATION.md) - GPS-free configuration guide
- [README.md](../README.md) - Project setup and quick start

---

**Last Updated**: 2025-11-10
