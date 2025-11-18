# Development Guidelines - Artefac Drone Defense

**Project**: Multi-drone simulation system for crisis delivery missions
**Team**: Evolutek
**Technology Stack**: PX4 v1.16.0 + Gazebo Harmonic + ROS2 Humble + FastAPI

---

## Architecture Overview

### Technology Stack (Updated 2025-11-04)

| Component | Version | Purpose |
|-----------|---------|---------|
| PX4 Autopilot | v1.16.0 | Drone firmware (SITL mode) |
| Gazebo | Harmonic | Physics simulation (LTS until Sep 2027) |
| ROS2 | Humble Hawksbill | Middleware (LTS until May 2027) |
| MAVROS | humble | MAVLink ↔ ROS2 bridge |
| MQTT | Eclipse Mosquitto 2.0 | Message broker for ROS2 ↔ Backend |
| Ubuntu | 22.04 LTS | Container base |
| Python | 3.10 | Backend runtime |
| FastAPI | Latest | REST API framework |
| React | 18 + Vite | Frontend UI |

### Container Structure

```
simulation/     - PX4 SITL + Gazebo Harmonic (gz sim)
ros2_integration/      - ROS2 Humble + MAVROS + mqtt_bridge package
mqtt/           - Eclipse Mosquitto MQTT broker
backend/        - FastAPI + SQLite + MQTT client + WebSocket
frontend/       - React + TypeScript + Nginx
```

---

## Development Rules

### Code Style
- Python: Follow PEP 8
- ROS2: Follow ROS 2 naming conventions
- Comments and docs: English only
- Commit messages: English, conventional commits format

### Git Workflow
- Never commit to main directly
- Always work on feature branches
- Branch naming: `feature/description`, `fix/description`, `architecture/description`
- Commits: Clear, atomic changes with descriptive messages

### Docker Best Practices
- Always pin versions (no `latest` tags in production)
- Use build caches (named volumes for build artifacts)
- network_mode: host required for ROS2 DDS multicast
- Separate concerns: simulation, middleware, backend

### ROS2 Guidelines
- Use namespaces for multi-drone: `/drone_N/mavros/*`
- Topic naming: lowercase with underscores
- Launch files: Python-based (not XML)
- QoS profiles: Match requirements (reliable vs best-effort)

### Claude Code Agents
- **docu-dude**: Use this agent for documentation tasks (reviewing, updating, or synchronizing documentation files like CLAUDE.md, README.md, etc.)
- Always use specialized agents when their expertise matches the task at hand

---

## Key Environment Variables

### PX4 Simulation
```bash
PX4_HOME_LAT=43.6047          # Toulouse coordinates
PX4_HOME_LON=1.4442
PX4_SIM_MODEL=gz_x500         # Default model for Gazebo Harmonic
PX4_GZ_WORLD=default          # World file name
HEADLESS=0                     # 0=GUI, 1=headless
```

### X11 Display (for Gazebo GUI)
**⚠️ DISPLAY is auto-detected from your shell environment - no manual configuration needed!**

The `./start.sh` script automatically configures X11 based on `HOST_OS` in `.env`.

**Important**:
- `DISPLAY` is inherited from your shell (e.g., `:0` on X11, `:1` on Wayland+XWayland)
- Do NOT set `DISPLAY` in `.env` unless you need to override (e.g., remote X11)
- Use `./start.sh` instead of `docker compose` directly

```bash
# Linux - Auto-detected (nothing to configure)
# The script detects :0 (X11) or :1 (Wayland+XWayland) automatically

# macOS (requires XQuartz)
# Override in .env only if auto-detection fails:
# DISPLAY=host.docker.internal:0

# Windows WSL2 (requires VcXsrv/X410)
# Must set in .env:
# DISPLAY=<WINDOWS_HOST_IP>:0  # Get IP from: ipconfig in Windows
```

**Troubleshooting**:
- Ubuntu 25.04+ often uses Wayland → DISPLAY=:1 (XWayland)
- If GUI doesn't show: `echo $DISPLAY` and verify it's not hardcoded in `.env`

### ROS2
```bash
ROS_DOMAIN_ID=42              # Must match across all ROS2 containers
RMW_IMPLEMENTATION=rmw_fastrtps_cpp
FASTRTPS_DEFAULT_PROFILES_FILE=/root/fastdds.xml
```

### Gazebo Harmonic
```bash
GZ_SIM_RESOURCE_PATH=/root/PX4-Autopilot/Tools/simulation/gz/models:/root/PX4-Autopilot/Tools/simulation/gz/worlds
GZ_SIM_SYSTEM_PLUGIN_PATH=/root/PX4-Autopilot/build/px4_sitl_default/build_gz
```

---

## Common Commands

### Build & Run
```bash
# Build all containers
docker compose build

# Run simulation + ROS2 + backend
docker compose up

# Run only simulation (headless)
HEADLESS=1 docker compose up simulation

# Clean rebuild
docker compose down -v
docker compose build --no-cache
```

### ROS2 Debugging
```bash
# List topics
docker exec -it artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic list"

# Monitor MAVROS state
docker exec -it artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic echo /mavros/state"

# Check node connectivity
docker exec -it artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 node list"
```

### PX4 Debugging
```bash
# Access PX4 shell
docker exec -it artefac_simulation bash

# Check Gazebo Harmonic process
ps aux | grep "gz sim"

# View PX4 logs
tail -f /root/.ros/log/*/px4.log
```

---

## Multi-Drone Configuration

### Port Allocation
```
Drone N:
  MAVLink:     14540 + N
  Simulator:   18570 + N
  Namespace:   /drone_N
  System ID:   N + 1
```

### Available Models (Gazebo Harmonic)
- `gz_x500` - Standard quadcopter (default)
- `gz_x500_depth` - With depth camera
- `gz_rc_cessna` - Fixed-wing
- Custom models in `simulation/models/`

### Dynamic Drone Management ⭐ NEW

**Spawn/Despawn drones at runtime** without restarting the simulation:

```bash
# Add a drone dynamically
docker exec -it artefac_ros2_integration bash -c "cd /root && bash simulation/spawn_drone.sh 0"
# → Spawns drone_1 (x500_0) at default position

docker exec -it artefac_ros2_integration bash -c "cd /root && bash simulation/spawn_drone.sh 1 5 5 0.5"
# → Spawns drone_2 (x500_1) at position (5, 5, 0.5)

# Remove a drone
docker exec -it artefac_ros2_integration bash -c "cd /root && bash simulation/despawn_drone.sh 0"
# → Removes drone_1

# List active drones
docker exec -it artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic list | grep /drone_"
```

**What happens when spawning:**
1. Gazebo spawns `x500_N` model at specified position
2. PX4 SITL instance N starts (port 14540+N)
3. MAVROS + vision_bridge + mqtt_bridge launch for `/drone_N/` namespace
4. Drone operational in ~10-15 seconds

**Current limitations:**
- Manual spawn/despawn via shell scripts (API coming in v2)
- Max ~5-6 drones on 8-core CPU (physics real-time constraint)
- Drone numbering must be sequential for now (0, 1, 2, ...)

**Roadmap (Option B - Full System):**
- [ ] Backend API: `POST /drones/spawn`, `DELETE /drones/{id}`
- [ ] Frontend UI: Add/Remove drone buttons
- [ ] Auto port/ID management
- [ ] Drone placement grid visualization

---

## Troubleshooting

### Gazebo Harmonic doesn't start
1. Check GPU access: `nvidia-smi` (if using GPU)
2. Verify X11 forwarding: `echo $DISPLAY`
3. Check gz sim process: `ps aux | grep "gz sim"`
4. View logs: `docker compose logs simulation`

### macOS-specific issues

#### XQuartz authorization errors
**Symptom**: `xauth: error in locking authority file ~/.docker.xauth`

**Root cause**: The xauth command was trying to lock a file that already existed with incorrect permissions or was in use.

**Solution**: The start script now automatically removes and recreates the xauth file with proper permissions. The Docker volume mount has also been fixed to map correctly from host (`$HOME/.docker.xauth`) to container (`/root/.docker.xauth`).

If the issue persists:
```bash
# Manually clean up
rm -f ~/.docker.xauth
./start.sh up simulation
```

#### Headless mode forced despite XQuartz running
**Symptom**: Logs show `Headless mode: 1` even with XQuartz configured

**Solution**: The start script now automatically forces `HEADLESS=0` on macOS. Verify your `.env` file doesn't override this after script execution.

#### Sensor timeout errors (Accel #0 fail: TIMEOUT)
**Symptom**: `ERROR [sensors] Accel #0 fail: TIMEOUT!` and `ekf2 missing data`

**Root cause**: Gazebo Harmonic in Docker on macOS has issues communicating sensor data to PX4 in headless mode.

**Solution**:
1. Ensure XQuartz is running with "Allow connections from network clients" enabled
2. The start script forces GUI mode (`HEADLESS=0`) automatically
3. Rebuild the simulation container: `docker compose build simulation`
4. Restart: `./start.sh up simulation`

#### Parameter calculation errors (bc: not found)
**Symptom**: `etc/init.d-posix/rcS: 196: bc: not found` and parameter errors like `COM_DL_LOSS_T set to <empty>`

**Solution**: Rebuild the simulation container (the fix is now in Dockerfile.px4):
```bash
docker compose build simulation --no-cache
./start.sh up simulation
```

### MAVROS not connecting
1. Verify PX4 MAVLink port: `netstat -tulpn | grep 14540`
2. Check MAVROS launch file FCU URL
3. Ensure network_mode: host in docker-compose.yml
4. Verify ROS_DOMAIN_ID matches

### ROS2 nodes can't discover each other
1. Check ROS_DOMAIN_ID consistency
2. Verify network_mode: host
3. Test DDS: `ros2 daemon stop && ros2 daemon start`
4. Check FastDDS config: `simulation/config/fastdds.xml`

---

## File Structure

```
artefac-drone-defense/
├── .claude/plan/                    # Development plans
├── backend/                         # FastAPI application
│   ├── app/
│   │   ├── main.py                  # FastAPI app with REST endpoints
│   │   ├── mqtt_client.py           # MQTT client for ROS2 bridge
│   │   ├── websocket_manager.py     # WebSocket real-time updates
│   │   ├── models/                  # SQLAlchemy models (Drone, Telemetry, Mission)
│   │   ├── crud/                    # Database operations
│   │   └── schemas.py               # Pydantic models
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                        # React + TypeScript UI
│   ├── src/
│   │   ├── App.tsx                  # Main app component
│   │   ├── components/
│   │   │   ├── HealthDashboard.tsx  # System health monitoring
│   │   │   ├── DroneControl.tsx     # ARM/DISARM/TAKEOFF/LAND buttons
│   │   │   └── DroneTelemetry.tsx   # Real-time telemetry display
│   │   └── utils/api.ts             # API client
│   ├── Dockerfile                   # Multi-stage build with Nginx
│   └── package.json
├── simulation/
│   ├── src/
│   │   ├── mavros_launcher/         # ROS2 MAVROS launch files
│   │   └── mqtt_bridge/             # ROS2 ↔ MQTT bridge node ⭐ NEW
│   │       ├── mqtt_bridge/
│   │       │   └── bridge_node.py   # Bridges MAVROS topics to MQTT
│   │       ├── launch/
│   │       │   └── mqtt_bridge.launch.py
│   │       └── package.xml
│   ├── config/
│   │   └── fastdds.xml              # DDS configuration
│   ├── gazebo_worlds/               # Custom Gazebo worlds
│   ├── models/                      # Custom drone models
│   ├── Dockerfile                   # ROS2 + MAVROS + paho-mqtt
│   └── Dockerfile.px4               # PX4 + Gazebo Harmonic
├── mqtt/
│   └── config/
│       └── mosquitto.conf           # MQTT broker config
├── logs/                            # Container logs (gitignored)
├── docker-compose.yml               # 5 services (simulation, ros2_integration, mqtt, backend, frontend)
├── .env.example
├── CLAUDE.md                        # This file
└── README.md
```

---

## Important Notes

### MVP Web Control System (Nov 2025) ✅ COMPLETE

**Architecture**: Frontend → Backend (HTTP/WebSocket) → MQTT → ROS2 Bridge → MAVROS → PX4

**Key Components**:
1. **MQTT Bridge** (`simulation/src/mqtt_bridge`)
   - Subscribes to MAVROS topics: `/drone_N/mavros/state`, `/drone_N/mavros/local_position/pose`, `/drone_N/mavros/battery`
   - Publishes to MQTT: `drone/{id}/state`, `drone/{id}/telemetry`, `drone/{id}/command_result`
   - Subscribes to MQTT: `drone/{id}/command`
   - Calls MAVROS services: `/drone_N/mavros_node/arming`, `/drone_N/mavros_node/cmd/takeoff`, `/drone_N/mavros_node/cmd/land`
   - **Multi-drone namespace**: All topics/services use `/drone_N/` prefix (verified 2025-11-17)

2. **Backend API** (FastAPI)
   - REST endpoints: `/drones/{id}/arm`, `/drones/{id}/disarm`, `/drones/{id}/takeoff`, `/drones/{id}/land`
   - Synchronous command execution with result feedback
   - WebSocket: `/ws/drone/{id}` for real-time telemetry
   - SQLite database for persistence
   - Auto-registration of drones from telemetry

3. **Frontend UI** (React + TypeScript)
   - Health dashboard showing system status
   - Drone control panel with ARM/DISARM toggle switch
   - Real-time error/success messages from command execution
   - Real-time telemetry display via WebSocket
   - Accessible at http://localhost:3000

**MQTT Topics**:
- `drone/{id}/state` - Drone state (connected, armed, mode) - Published by ROS2 bridge
- `drone/{id}/telemetry` - Position, velocity, battery - Published by ROS2 bridge
- `drone/{id}/command` - Commands (ARM, DISARM, TAKEOFF, LAND) - Subscribed by ROS2 bridge
- `drone/{id}/command_result` - Command execution results (success/error) - Published by ROS2 bridge

**Critical ROS2/MAVROS Fixes**:
- ⚠️ MAVROS publishes state on `/drone_N/mavros/state` with namespace prefix
- ⚠️ MAVROS services are under `/drone_N/mavros_node/*` namespace (not `/mavros/cmd/*`)
- ⚠️ `/drone_N/mavros/state` topic requires QoS RELIABLE + TRANSIENT_LOCAL
- ⚠️ All MAVROS topics use `/drone_N/mavros/*` prefix in multi-drone setup

### Gazebo Harmonic Migration (Nov 2025)
- Migrated from Gazebo Classic to Gazebo Harmonic
- Uses `gz sim` commands instead of `gazebo`/`gzserver`
- Models in `~/.gz/sim/` instead of `~/.gazebo/`
- Environment variables: `GZ_SIM_*` instead of `GAZEBO_*`
- PX4 build target: `gz_x500` instead of `gazebo-classic`
- ROS2 integration: `ros_gz` instead of `gazebo_ros_pkgs`

### Backend Architecture Decision
Backend is **pure Python without ROS2** for production deployability. MQTT bridge service handles ROS2 ↔ Backend communication.

### Sensor Integration Status (Verified 2025-11-17)

**All Essential Sensors Operational**:
- ✅ IMU (Accel + Gyro): `/drone_1/mavros/imu/data` @ ~10 Hz
- ✅ Magnetometer: `/drone_1/mavros/mag` @ ~14 Hz
- ✅ Barometer: `/drone_1/mavros/imu/static_pressure` @ ~16 Hz
- ✅ GPS: `/drone_1/mavros/global_position/raw/fix` @ ~30 Hz (active and fused by EKF2)
- ✅ MAVROS connected to PX4 via MAVLink port 14540

**GPS Configuration Notes**:
GPS sensor is enabled and used as the primary source for horizontal position and velocity estimation. EKF2 fuses GPS with IMU, magnetometer, and barometer for robust 3D positioning. Vision bridge node remains active but vision fusion is disabled in MAVROS configuration (`use_vision: false`).

### PX4 Arming Behavior - GPS-Enabled Configuration

**Current Status**: GPS-enabled mode operational with full 3D position estimation

**EKF2 Convergence Status (Verified 2025-11-18)**:

Operating in GPS-enabled mode:
- ✅ `attitude_status_flag: true` - Roll/pitch/yaw estimated from IMU+Magnetometer
- ✅ `velocity_vert_status_flag: true` - Vertical velocity from IMU+Barometer
- ✅ `pos_vert_abs_status_flag: true` - Altitude from barometer/GPS
- ✅ `velocity_horiz_status_flag: true` - Horizontal velocity from GPS fusion
- ✅ `pos_horiz_rel_status_flag: true` - Horizontal position from GPS fusion
- ✅ `pos_horiz_abs_status_flag: true` - GPS absolute positioning ACTIVE (key indicator)

**Conclusion**: EKF2 successfully converges for full 3D position and velocity estimation using GPS as the primary localization source. GPS-enabled operation confirmed through behavioral verification.

**GPS-Enabled Configuration Implemented**:
- Parameters injected into PX4 startup (rcS patching)
- `COM_ARM_WO_GPS=0` - Require GPS fix for arming
- `EKF2_GPS_CTRL=7` - Enable GPS horizontal + vertical fusion (0b0111)
- `EKF2_HGT_REF=1` - Use GPS for height reference
- `MAV_*_BROADCAST=1` - Enable MAVLink network broadcast
- Vision fusion disabled via MAVROS config (`use_vision: false`)

**Verification Method**:
- Behavioral verification via `/drone_1/estimator_status` topic (not log parsing)
- GPS mode confirmed when `pos_horiz_abs_status_flag=true` (GPS absolute position active)
- Integration test uses real-time topic observation for robust validation

### Known Issues

No critical issues at this time. All integration tests passing.

### Testing Protocol
- I always run tests myself then tell you the result
- I always compile project myself then tell you the result
- Never mock tests - use real data dynamically
- Tests cannot be modified unless specified

**Integration Test Status (Updated 2025-11-18)**:
- Phase 1: Sensor initialization (IMU, Mag, Baro, GPS) - PASSES ✅
- Phase 1: GPS fix verification (satellites ≥6, good HDOP) - PASSES ✅
- Phase 2: GPS-enabled parameters verification (behavioral) - PASSES ✅
- Phase 2: MAVROS connection - PASSES ✅
- Phase 2: EKF2 initialization - PASSES ✅
- Phase 3: EKF2 estimator status (full 3D GPS fusion) - PASSES ✅

**Testing Methodology**:
- Tests use behavioral verification instead of log parsing for robustness
- GPS-enabled operation verified through EKF2 estimator status flags on `/drone_1/estimator_status`
- GPS fusion confirmed by: `pos_horiz_abs_status_flag=true` (absolute position active)
- All tests use direct topic/service observations for real-world validation

---

**Last Updated**: 2025-11-18
**Status**: All integration tests passing ✅ | Sensor integration verified ✅ | GPS mode operational ✅ | Full 3D positioning active ✅
