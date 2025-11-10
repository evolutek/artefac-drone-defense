# Communication Flow - Artefac Drone Defense

This document explains the complete communication flow between all system components, from user interaction to drone response.

## System Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│    MQTT     │────▶│ ROS2 Bridge │────▶│   MAVROS    │
│  (React UI) │◀────│  (FastAPI)  │◀────│   Broker    │◀────│  (Python)   │◀────│   + PX4     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     HTTP/WS            MQTT Client        Eclipse              ROS2 Node          MAVLink
                                         Mosquitto
```

## Component Responsibilities

| Component | Technology | Port | Role |
|-----------|-----------|------|------|
| **Frontend** | React + TypeScript + Vite | 3000 | User interface, command input, telemetry display |
| **Backend** | FastAPI + SQLite + paho-mqtt | 8000 | REST API, MQTT client, WebSocket server, persistence |
| **MQTT Broker** | Eclipse Mosquitto | 1883 | Message broker between backend and ROS2 |
| **ROS2 Bridge** | ROS2 Humble + paho-mqtt | - | MQTT ↔ ROS2 bridge, MAVROS service caller |
| **MAVROS** | ROS2 + MAVLink | - | ROS2 ↔ MAVLink bridge |
| **PX4 SITL** | PX4 Autopilot v1.16.0 | 14540 | Drone firmware simulation |

---

## Key Terminology

### MAVLink (Low-Level Protocol)
- **What it is**: Binary protocol for drone communication
- **Message types**: `HEARTBEAT`, `GPS_RAW_INT`, `VISION_POSITION_ESTIMATE`, etc.
- **Transport**: TCP/UDP/Serial
- **Used by**: PX4 ↔ MAVROS communication

### MAVROS (ROS2 ↔ MAVLink Translator)
- **What it is**: ROS2 node that translates MAVLink to ROS2 Topics/Services
- **Architecture**: Plugin-based (sys_status, local_position, command, vision_pose, etc.)
- **Exposes**:
  - **Services**: `/mavros_node/arming`, `/mavros_node/set_mode`, `/mavros_node/cmd/takeoff`, `/mavros_node/cmd/land`
  - **Topics**: `/mavros/state`, `/mavros/local_position/pose`, `/mavros/vision_pose/pose`
- **Note**: Don't confuse `/mavros_node/arming` (service) with `/mavros/cmd/arming` (topic)

### Pose (Position + Orientation)
- **Position**: `(x, y, z)` in meters
- **Orientation**: Quaternion `(x, y, z, w)` for 3D rotation
- **Example**: `/mavros/local_position/pose` = where the drone is and which direction it's pointing

### EKF2 (Extended Kalman Filter)
- **What it is**: PX4's state estimator that fuses sensor data
- **Inputs**: IMU, GPS, barometer, vision, magnetometer
- **Output**: Estimated position, velocity, attitude
- **GPS-free**: Can be configured to use vision data instead of GPS (see `GPS_FREE_OPERATION.md`)

### MQTT Bridge (ROS2 ↔ MQTT Translator)
- **Listens to**: ROS2 topics (`/mavros/state`, `/mavros/local_position/pose`)
- **Publishes to**: MQTT (`drone/drone_1/telemetry`)
- **Calls**: ROS2 services (`/mavros_node/arming`) when MQTT commands received

---

## Communication Protocols

### 1. Frontend ↔ Backend
- **REST API (HTTP)**: Command requests with synchronous error handling
- **WebSocket**: Real-time telemetry and state updates

### 2. Backend ↔ MQTT Broker
- **MQTT Topics**:
  - `drone/{id}/command` - Commands to drone (QoS 1)
  - `drone/{id}/telemetry` - Telemetry data (QoS 1)
  - `drone/{id}/state` - Drone state (QoS 1, retained)
  - `drone/{id}/command_result` - Command execution results (QoS 1)

### 3. ROS2 Bridge ↔ MAVROS
- **ROS2 Topics** (telemetry from drone):
  - `/mavros/state` - MAVROS state (QoS: RELIABLE, TRANSIENT_LOCAL)
  - `/mavros/local_position/pose` - Local position (x, y, z + orientation)
  - `/mavros/global_position/global` - GPS position (lat, lon, alt)
  - `/mavros/battery` - Battery status (voltage, current, %)
  - `/mavros/local_position/velocity_local` - Velocity (vx, vy, vz)
- **ROS2 Services** (commands to drone):
  - `/mavros_node/arming` - ARM/DISARM service
  - `/mavros_node/cmd/takeoff` - Takeoff service
  - `/mavros_node/cmd/land` - Land service
  - `/mavros_node/set_mode` - Flight mode service

**Note**: Do NOT confuse `/mavros_node/arming` (service) with `/mavros/cmd/arming` (topic). The MQTT bridge uses **services**, not topics.

---

## Detailed Communication Flows

### Flow 1: ARM Command (Success Case)

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│ Frontend │      │ Backend  │      │   MQTT   │      │   ROS2   │      │  MAVROS  │
│          │      │          │      │  Broker  │      │  Bridge  │      │   PX4    │
└────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                 │                 │                 │
     │ 1. POST /arm    │                 │                 │                 │
     │────────────────▶│                 │                 │                 │
     │                 │                 │                 │                 │
     │                 │ 2. MQTT Publish │                 │                 │
     │                 │ drone/1/command │                 │                 │
     │                 │ {"command":"ARM"}                 │                 │
     │                 │────────────────▶│                 │                 │
     │                 │                 │                 │                 │
     │                 │                 │ 3. MQTT Message │                 │
     │                 │                 │────────────────▶│                 │
     │                 │                 │                 │                 │
     │                 │                 │                 │ 4. Service Call │
     │                 │                 │                 │ /mavros_node/   │
     │                 │                 │                 │    arming       │
     │                 │                 │                 │ value=true      │
     │                 │                 │                 │────────────────▶│
     │                 │                 │                 │                 │
     │                 │                 │                 │ 5. Response     │
     │                 │                 │                 │ success=true    │
     │                 │                 │                 │◀────────────────│
     │                 │                 │                 │                 │
     │                 │                 │ 6. MQTT Publish │                 │
     │                 │                 │ drone/1/        │                 │
     │                 │                 │ command_result  │                 │
     │                 │                 │ {"success":true}│                 │
     │                 │                 │◀────────────────│                 │
     │                 │                 │                 │                 │
     │                 │ 7. Result       │                 │                 │
     │                 │◀────────────────│                 │                 │
     │                 │                 │                 │                 │
     │ 8. HTTP 200     │                 │                 │                 │
     │ {success:true,  │                 │                 │                 │
     │  message:"Drone │                 │                 │                 │
     │  armed"}        │                 │                 │                 │
     │◀────────────────│                 │                 │                 │
     │                 │                 │                 │                 │
```

**Timing**: ~50-200ms total (depends on ROS2 service call latency)

---

### Flow 2: ARM Command (Failure Case - PX4 Rejects)

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│ Frontend │      │ Backend  │      │   MQTT   │      │   ROS2   │      │  MAVROS  │
│          │      │          │      │  Broker  │      │  Bridge  │      │   PX4    │
└────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                 │                 │                 │
     │ 1. POST /arm    │                 │                 │                 │
     │────────────────▶│                 │                 │                 │
     │                 │                 │                 │                 │
     │                 │ 2. MQTT Publish │                 │                 │
     │                 │────────────────▶│────────────────▶│                 │
     │                 │                 │                 │                 │
     │                 │ 3. Wait for     │                 │ 4. Service Call │
     │                 │    result       │                 │────────────────▶│
     │                 │    (5s timeout) │                 │                 │
     │                 │                 │                 │ 5. Response     │
     │                 │                 │                 │ ❌ success=false│
     │                 │                 │                 │ (no GPS fix)    │
     │                 │                 │                 │◀────────────────│
     │                 │                 │                 │                 │
     │                 │                 │ 6. MQTT Publish │                 │
     │                 │                 │ command_result  │                 │
     │                 │                 │ {success:false, │                 │
     │                 │                 │  message:"PX4   │                 │
     │                 │                 │  rejected - no  │                 │
     │                 │                 │  GPS fix"}      │                 │
     │                 │                 │◀────────────────│                 │
     │                 │                 │                 │                 │
     │                 │ 7. Result       │                 │                 │
     │                 │◀────────────────│                 │                 │
     │                 │                 │                 │                 │
     │ 8. HTTP 400     │                 │                 │                 │
     │ {detail:"Failed │                 │                 │                 │
     │  to arm drone - │                 │                 │                 │
     │  PX4 rejected   │                 │                 │                 │
     │  command..."}   │                 │                 │                 │
     │◀────────────────│                 │                 │                 │
     │                 │                 │                 │                 │
     │ 9. Display Error│                 │                 │                 │
     │ ❌ "Failed to   │                 │                 │                 │
     │ arm drone - PX4 │                 │                 │                 │
     │ rejected..."    │                 │                 │                 │
     │                 │                 │                 │                 │
```

**Error Types**:
- **400 Bad Request**: PX4 rejected command (no GPS fix, not in correct mode, safety checks)
- **503 Service Unavailable**: MQTT broker not connected
- **504 Gateway Timeout**: ROS2 bridge not responding (5s timeout)

---

### Flow 3: ARM Command (Timeout Case - ROS2 Bridge Offline)

```
┌──────────┐      ┌──────────┐      ┌──────────┐
│ Frontend │      │ Backend  │      │   MQTT   │      ❌ ROS2 Bridge Offline
│          │      │          │      │  Broker  │
└────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                 │
     │ 1. POST /arm    │                 │
     │────────────────▶│                 │
     │                 │                 │
     │                 │ 2. MQTT Publish │
     │                 │────────────────▶│
     │                 │                 │ (no subscriber)
     │                 │                 │
     │                 │ 3. Wait 5s...   │
     │                 │ ⏱️              │
     │                 │ ⏱️              │
     │                 │ ⏱️              │
     │                 │ ❌ Timeout!     │
     │                 │                 │
     │ 4. HTTP 504     │                 │
     │ {detail:"Timeout│                 │
     │  waiting for    │                 │
     │  drone response"│                 │
     │◀────────────────│                 │
     │                 │                 │
     │ 5. Display Error│                 │
     │ ❌ "Timeout     │                 │
     │ waiting for     │                 │
     │ drone response" │                 │
     │                 │                 │
```

---

### Flow 4: Real-time Telemetry Updates

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│ Frontend │      │ Backend  │      │   MQTT   │      │   ROS2   │      │  MAVROS  │
│          │      │          │      │  Broker  │      │  Bridge  │      │          │
└────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                 │                 │                 │
     │ 1. Connect WS   │                 │                 │                 │
     │ /ws/drone/1     │                 │                 │                 │
     │────────────────▶│                 │                 │                 │
     │                 │                 │                 │                 │
     │                 │                 │                 │ 2. ROS2 Callback│
     │                 │                 │                 │ /state topic    │
     │                 │                 │                 │◀────────────────│
     │                 │                 │                 │                 │
     │                 │                 │ 3. MQTT Publish │                 │
     │                 │                 │ drone/1/state   │                 │
     │                 │                 │ {armed:true,    │                 │
     │                 │                 │  mode:"MANUAL"} │                 │
     │                 │                 │◀────────────────│                 │
     │                 │                 │                 │                 │
     │                 │ 4. MQTT Callback│                 │                 │
     │                 │◀────────────────│                 │                 │
     │                 │                 │                 │                 │
     │ 5. WS Message   │                 │                 │                 │
     │ {type:"state",  │                 │                 │                 │
     │  data:{armed:   │                 │                 │                 │
     │  true}}         │                 │                 │                 │
     │◀────────────────│                 │                 │                 │
     │                 │                 │                 │                 │
     │ 6. Update UI    │                 │                 │                 │
     │ 🔄 Switch turns │                 │                 │                 │
     │    GREEN        │                 │                 │                 │
     │                 │                 │                 │                 │
```

**Update Frequency**:
- **State**: Published on change (retained)
- **Telemetry**: Published every 500ms (2 Hz)

---

## MQTT Topics Reference

### Commands (Backend → ROS2 Bridge)

**Topic**: `drone/{drone_id}/command`
**QoS**: 1 (at least once)
**Retained**: No

**Payload Format**:
```json
{
  "command": "ARM|DISARM|TAKEOFF|LAND",
  "params": {
    "altitude": 5.0  // For TAKEOFF only
  },
  "timestamp": 1234567890
}
```

**Example**:
```json
{
  "command": "ARM",
  "timestamp": 1699876543
}
```

---

### Command Results (ROS2 Bridge → Backend)

**Topic**: `drone/{drone_id}/command_result`
**QoS**: 1 (at least once)
**Retained**: No

**Payload Format**:
```json
{
  "command": "ARM|DISARM|TAKEOFF|LAND",
  "success": true|false,
  "message": "Human-readable result message",
  "timestamp": 1234567890
}
```

**Success Example**:
```json
{
  "command": "ARM",
  "success": true,
  "message": "Drone armed successfully",
  "timestamp": 1699876544
}
```

**Failure Example**:
```json
{
  "command": "ARM",
  "success": false,
  "message": "Failed to arm drone - PX4 rejected command (check GPS fix, flight mode, or safety checks)",
  "timestamp": 1699876544
}
```

---

### Telemetry (ROS2 Bridge → Backend)

**Topic**: `drone/{drone_id}/telemetry`
**QoS**: 1 (at least once)
**Retained**: No
**Frequency**: 2 Hz (every 500ms)

**Payload Format**:
```json
{
  "position_x": 0.0,
  "position_y": 0.0,
  "position_z": 0.0,
  "latitude": 43.6047,
  "longitude": 1.4442,
  "altitude": 150.5,
  "velocity_x": 0.0,
  "velocity_y": 0.0,
  "velocity_z": 0.0,
  "orientation_x": 0.0,
  "orientation_y": 0.0,
  "orientation_z": 0.0,
  "orientation_w": 1.0,
  "battery": 95.5
}
```

---

### State (ROS2 Bridge → Backend)

**Topic**: `drone/{drone_id}/state`
**QoS**: 1 (at least once)
**Retained**: Yes (last state preserved)
**Frequency**: On change

**Payload Format**:
```json
{
  "connected": true,
  "armed": false,
  "mode": "MANUAL"
}
```

---

## Error Handling Matrix

| Error Scenario | HTTP Status | Frontend Display | Backend Action | ROS2 Bridge Action |
|---------------|-------------|------------------|----------------|-------------------|
| PX4 rejects command | 400 | Show error message from PX4 | Return error from wait_for_command_result() | Publish command_result with success=false |
| MQTT broker offline | 503 | "MQTT broker not available" | publish_command() returns false | N/A |
| ROS2 bridge timeout | 504 | "Timeout waiting for response" | wait_for_command_result() returns None after 5s | N/A |
| MAVROS service unavailable | 400 | "Service not available" | Receive error from command_result | Publish command_result with error |
| Drone not registered | 404 | "Drone not found" | Check database before publish | N/A |

---

## Timing Expectations

| Operation | Expected Latency | Timeout |
|-----------|-----------------|---------|
| Frontend → Backend HTTP | 5-20ms | 30s (browser default) |
| Backend → MQTT Publish | 1-5ms | N/A |
| MQTT → ROS2 Bridge | 5-15ms | N/A |
| ROS2 Service Call | 20-100ms | Service-specific |
| Command Result Wait | 50-200ms total | 5s (backend) |
| WebSocket Update | 10-50ms | N/A |
| Telemetry Frequency | Every 500ms | N/A |

---

## Troubleshooting Guide

### Problem: Frontend shows "Failed to send ARM command" but no details

**Diagnosis**:
```bash
# Check backend logs
docker compose logs backend --tail 50

# Check MQTT messages
docker exec artefac_mqtt mosquitto_sub -t "drone/#" -v
```

**Common Causes**:
1. MQTT broker not running
2. ROS2 bridge not subscribed to command topic
3. Backend timeout (5s)

---

### Problem: Command sent but no response

**Diagnosis**:
```bash
# Check if ROS2 bridge receives command
docker compose logs ros2_integration | grep "Received command"

# Check if MAVROS service responds
docker exec -it artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 service call /mavros_node/arming mavros_msgs/srv/CommandBool '{value: true}'"
```

**Common Causes**:
1. MAVROS not connected to PX4
2. PX4 SITL not running
3. ROS2 bridge crashed

---

### Problem: PX4 always rejects ARM command

**Reason**: This is **expected behavior** in default SITL configuration.

**Why**: PX4 requires:
- Valid GPS fix (or GPS disabled)
- Correct flight mode (MANUAL/STABILIZED or OFFBOARD)
- Safety checks passed

**Solutions**:
1. **Enable OFFBOARD mode** before arming
2. **Disable GPS requirement**: `param set COM_ARM_WO_GPS 1` in PX4 shell
3. **Use external GPS simulator** with valid fix

**This is NOT a bug** - it's a safety feature of PX4.

---

## WebSocket Protocol

### Connection

**Endpoint**: `ws://localhost:8000/ws/drone/{drone_id}`

**Authentication**: None (TODO: Add in production)

### Messages from Backend → Frontend

**Format**:
```json
{
  "type": "telemetry" | "state",
  "drone_id": "drone_1",
  "data": {
    // Telemetry or state data
  }
}
```

**Example - Telemetry**:
```json
{
  "type": "telemetry",
  "drone_id": "drone_1",
  "data": {
    "position_x": 0.0,
    "position_z": 5.2,
    "battery": 87.3
  }
}
```

**Example - State**:
```json
{
  "type": "state",
  "drone_id": "drone_1",
  "data": {
    "connected": true,
    "armed": true,
    "mode": "OFFBOARD"
  }
}
```

---

## Security Considerations

### Current (MVP) - Development Only
- ⚠️ **No authentication** on API endpoints
- ⚠️ **No authorization** on drone commands
- ⚠️ **No encryption** on WebSocket
- ⚠️ **No rate limiting**
- ⚠️ CORS allows all origins

### Production Requirements (TODO)
- ✅ JWT authentication on REST endpoints
- ✅ WebSocket authentication handshake
- ✅ SSL/TLS for all connections
- ✅ Role-based access control (RBAC)
- ✅ Rate limiting per user/IP
- ✅ Command validation and logging
- ✅ Restricted CORS origins

---

## Performance Metrics

### Target Performance
- Command latency: < 200ms (p95)
- Telemetry update rate: 2 Hz stable
- WebSocket message rate: 10-20 msg/s per drone
- Concurrent drones: 10+ without degradation

### Monitoring
```bash
# Backend metrics (TODO: Add Prometheus)
curl http://localhost:8000/health

# MQTT broker stats
docker exec artefac_mqtt mosquitto_sub -t '$SYS/broker/messages/received' -v

# ROS2 topic bandwidth
docker exec -it artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic bw /mavros/local_position/pose"
```

---

## Related Documentation

- [README.md](../README.md) - Project overview and setup
- [CLAUDE.md](../CLAUDE.md) - Development guidelines
- [DISPLAY_SETUP.md](../DISPLAY_SETUP.md) - X11 display configuration
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture details

---

**Last Updated**: 2025-11-04
**Status**: MVP Complete with error handling ✅
