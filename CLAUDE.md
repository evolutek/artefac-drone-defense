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
ros2_core/      - ROS2 Humble + MAVROS + mqtt_bridge package
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
**⚠️ See [DISPLAY_SETUP.md](DISPLAY_SETUP.md) for detailed multi-OS setup**
```bash
# Linux
DISPLAY=:0
XAUTHORITY=/tmp/.docker.xauth
# Required: xhost +local:docker

# macOS (requires XQuartz)
DISPLAY=host.docker.internal:0

# Windows WSL2 (requires VcXsrv/X410)
DISPLAY=<WINDOWS_HOST_IP>:0
```

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
docker exec -it artefac_ros2_core bash -c "source /opt/ros/humble/setup.bash && ros2 topic list"

# Monitor MAVROS state
docker exec -it artefac_ros2_core bash -c "source /opt/ros/humble/setup.bash && ros2 topic echo /mavros/state"

# Check node connectivity
docker exec -it artefac_ros2_core bash -c "source /opt/ros/humble/setup.bash && ros2 node list"
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
├── docker-compose.yml               # 5 services (simulation, ros2_core, mqtt, backend, frontend)
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
   - Subscribes to MAVROS topics: `/mavros/state`, `/mavros/local_position/pose`, `/mavros/battery`
   - Publishes to MQTT: `drone/{id}/state`, `drone/{id}/telemetry`, `drone/{id}/command_result`
   - Subscribes to MQTT: `drone/{id}/command`
   - Calls MAVROS services: `/mavros_node/arming`, `/mavros_node/cmd/takeoff`, `/mavros_node/cmd/land`

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
- ⚠️ MAVROS publishes state on `/mavros/state` (not `/state`)
- ⚠️ MAVROS services are under `/mavros_node/*` namespace (not `/mavros/cmd/*`)
- ⚠️ `/mavros/state` topic requires QoS RELIABLE + TRANSIENT_LOCAL
- ⚠️ MAVROS publishes other topics with `/mavros/*` prefix

### Gazebo Harmonic Migration (Nov 2025)
- Migrated from Gazebo Classic to Gazebo Harmonic
- Uses `gz sim` commands instead of `gazebo`/`gzserver`
- Models in `~/.gz/sim/` instead of `~/.gazebo/`
- Environment variables: `GZ_SIM_*` instead of `GAZEBO_*`
- PX4 build target: `gz_x500` instead of `gazebo-classic`
- ROS2 integration: `ros_gz` instead of `gazebo_ros_pkgs`

### Backend Architecture Decision
Backend is **pure Python without ROS2** for production deployability. MQTT bridge service handles ROS2 ↔ Backend communication.

### PX4 Arming Behavior (WIP - GPS-Free Configuration)

**Current Status**: Attempting GPS-free arming configuration

PX4 SITL normally refuses arming without:
- Valid GPS fix, OR
- OFFBOARD mode enabled, OR
- Safety checks disabled (not recommended)

**GPS-Free Configuration Implemented**:
- Parameters injected into PX4 startup (rcS patching)
- `COM_ARM_WO_GPS=1` - Allow arming without GPS
- `EKF2_GPS_CTRL=0` - Disable GPS requirement in EKF2
- `MAV_*_BROADCAST=1` - Enable MAVLink network broadcast
- MAVLink localhost-only flag removed from px4-rc.mavlink

**Testing Required**: Verify if GPS-free arming works with current configuration

### Testing Protocol
- I always run tests myself then tell you the result
- I always compile project myself then tell you the result
- Never mock tests - use real data dynamically
- Tests cannot be modified unless specified

---

**Last Updated**: 2025-11-10
**Status**: Command feedback system implemented ✅ | Vision pose bridge operational @ 52Hz ✅ | macOS compatibility fixes applied ✅ | GPS-free arming under investigation 🔄
