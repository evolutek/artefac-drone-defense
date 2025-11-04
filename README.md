# Artefac Drone Defense - Team Evolutek<<
**Challenge 4**: Livraison en Situation de Crise  
**Event**: Hackathon Drone Defense organisé par Artefac  
**Team**: Evolutek<<  

## 🚀 Quick Start - MVP

**Test the complete stack in 3 commands:**

```bash
# 1. Build containers (first time)
docker compose build

# 2. Launch everything
docker compose up

# 3. Open web interface
# Visit: http://localhost:3000
```

**What you get:**
- ✅ **Web Interface** - Real-time drone control panel (React + TypeScript)
- ✅ **3D Simulation** - Physics-based drone in Gazebo Harmonic
- ✅ **Live Telemetry** - WebSocket streaming of position, velocity, battery
- ✅ **Full Integration** - ROS2 → MQTT → FastAPI → WebSocket → React

**Try it:**
1. Wait for containers to be healthy (~1-2 min)
2. Open http://localhost:3000
3. Click **ARM** → **TAKEOFF** → watch drone lift in Gazebo
4. Monitor real-time telemetry updates
5. Click **LAND** → **DISARM**

---

## Vue d'ensemble
Système de simulation multi-drones pour missions de livraison en zones de crise. Architecture distribuée permettant le contrôle simultané de plusieurs drones avec spécifications différentes (quadcopter, hexacopter, VTOL) via une interface web ou API REST.

**Capacités**:
- Simulation physique réaliste (PX4 autopilot + Gazebo Harmonic)
- Communication ROS2 standard (MAVROS bridge)
- MQTT messaging pour découplage ROS2 ↔ Backend
- Backend API REST + WebSocket déployable en production
- Frontend web React avec contrôle temps réel
- Architecture scalable (jusqu'à 10+ drones par instance)

## Documentation
- **[SETUP.md](SETUP.md)** - Installation guide (setup instructions, all OS)
- **[DISPLAY_SETUP.md](DISPLAY_SETUP.md)** - Gazebo GUI display setup (Linux/macOS/Windows X11 configuration)
- **[simulation/src/README.md](simulation/src/README.md)** - ROS2 workspace documentation

---

## Architecture
### Technology Stack & Rationale
| Component | Version | Why This Choice |
|-----------|---------|----------------|
| **PX4 Autopilot** | v1.16.0 | Stable release with native Gazebo Harmonic support, gz_x500 model, extensive multi-drone documentation |
| **Gazebo** | Harmonic | Latest LTS (support until Sep 2027), modern architecture, improved performance over Classic |
| **ROS2** | Humble Hawksbill | LTS (support until 2027), Ubuntu 22.04 LTS base, mature MAVROS implementation, ros_gz bridge |
| **MAVROS** | humble | Official PX4↔ROS2 bridge, MAVLink protocol translator, battle-tested |
| **MQTT (Mosquitto)** | 2.0 | Lightweight message broker, decouples ROS2 from backend, enables scalability |
| **Ubuntu** | 22.04 LTS (Jammy) | Common base for all containers, LTS until 2027, ROS2 Humble target |
| **Python** | 3.10 | Backend runtime, included in Ubuntu 22.04, FastAPI compatibility |
| **FastAPI** | 0.109.0 | Modern async Python framework, automatic OpenAPI docs, WebSocket support, production-ready |
| **React** | 18.2.0 | Modern UI library, component-based, excellent TypeScript support |
| **Vite** | 5.0.8 | Fast build tool, HMR for dev, optimized production builds |
| **TypeScript** | 5.3.3 | Type safety, better DX, catches errors at compile time |
| **TailwindCSS** | 3.3.6 | Utility-first CSS, rapid UI development, consistent design system |
| **Nginx** | Alpine | Lightweight web server, reverse proxy, production-ready static file serving |

### Container Architecture
```
┌──────────────────────────────────────────────────────────────────┐
│                     HOST MACHINE (Linux/WSL2/macOS)              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Container: simulation (PX4 + Gazebo Harmonic)             │  │
│  │  Base: Ubuntu 22.04                                        │  │
│  │  Size: ~3.0 GB                                             │  │
│  │                                                            │  │
│  │  Processes:                                                │  │
│  │    • gz sim - Gazebo Harmonic simulation engine            │  │
│  │    • px4 - SITL (Software-In-The-Loop) autopilot           │  │
│  │                                                            │  │
│  │  Responsibilities:                                         │  │
│  │    - Simulate drone physics (aerodynamics, collisions)     │  │
│  │    - Run PX4 firmware in software                          │  │
│  │    - Generate sensor data (GPS, IMU, magnetometer)         │  │
│  │    - Apply motor commands to physics                       │  │
│  │                                                            │  │
│  │  Protocol: MAVLink (UDP port 4560)                         │  │
│  │  ───────────────────────────────────────────────────────── │  │
│  │  Analogy: The physical drone + environment (hardware)      │  │
│  └──────────────────────┬─────────────────────────────────────┘  │
│                         │ MAVLink UDP                            │
│  ┌──────────────────────▼───────────────────────────────────┐    │
│  │  Container: ros2_core (MAVROS Bridge)                    │    │
│  │  Base: osrf/ros:humble-desktop-full-jammy                │    │
│  │  Size: ~3.5 GB                                           │    │
│  │                                                          │    │
│  │  Processes:                                              │    │
│  │    • ROS2 DDS daemon - Communication middleware          │    │
│  │    • mavros_node - MAVLink↔ROS2 translator               │    │
│  │    • (future) Custom nodes - Swarm coordination          │    │
│  │                                                          │    │
│  │  Responsibilities:                                       │    │
│  │    - Bridge MAVLink (binary) ↔ ROS2 topics (DDS)         │    │
│  │    - Manage drone namespaces (/drone_0, /drone_1...)     │    │
│  │    - Publish /mavros/state, /mavros/local_position/*     │    │
│  │    - Subscribe /mavros/setpoint_position/local           │    │
│  │    - TF transformations (coordinate frames)              │    │
│  │                                                          │    │
│  │  Protocol: ROS2 DDS (multicast, requires network_mode)   │    │
│  │  ─────────────────────────────────────────────────────── │    │
│  │  Analogy: Communication system (middleware)              │    │
│  └──────────────────────┬───────────────────────────────────┘    │
│                         │ Future: ROS2 Bridge Service            │
│  ┌──────────────────────▼───────────────────────────────────┐    │
│  │  Container: backend (FastAPI)                            │    │
│  │  Base: python:3.10-slim                                  │    │
│  │  Size: ~200 MB                                           │    │
│  │                                                          │    │
│  │  Processes:                                              │    │
│  │    • uvicorn - ASGI web server                           │    │
│  │    • FastAPI app - REST API                              │    │
│  │                                                          │    │
│  │  Responsibilities:                                       │    │
│  │    - Provide REST API endpoints                          │    │
│  │    - Mission CRUD operations                             │    │
│  │    - Drone status aggregation                            │    │
│  │    - Health monitoring                                   │    │
│  │    - (future) WebSocket real-time streaming              │    │
│  │                                                          │    │
│  │  Protocol: HTTP/HTTPS (port 8000)                        │    │
│  │  ─────────────────────────────────────────────────────── │    │
│  │  Analogy: Control tower (business logic)                 │    │
│  │                                                          │    │
│  │  Architecture Decision: NO ROS2 dependency               │    │
│  │    - Deployable to cloud/prod without ROS2               │    │
│  │    - Standard web stack (portable)                       │    │
│  │    - Bridge service will handle ROS2 communication       │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Network: Host mode (required for ROS2 DDS multicast)            │
│  Volumes: px4_build, ros2_install, ros2_build, backend_data      │
└──────────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions
#### 1. Why Gazebo Harmonic?
**Gazebo Harmonic** is the modern, performant choice:
- ✅ PX4 v1.16.0 native support (`make px4_sitl gz_x500`)
- ✅ Latest LTS release (support until September 2027)
- ✅ Better performance and rendering than Classic
- ✅ Modern modular architecture with improved APIs
- ✅ ROS 2 integration via `ros_gz` bridge
- ✅ Multi-drone support with improved resource management
- ✅ Active development and community support

#### 2. Why ROS2 Humble?
**Proven stack**:
```
PX4 v1.16.0 + Gazebo Harmonic + ROS2 Humble + MAVROS = ✅ PRODUCTION READY
```

- ✅ LTS support until May 2027
- ✅ Ubuntu 22.04 LTS base (same as all containers)
- ✅ `ros-humble-mavros` actively maintained
- ✅ `ros-humble-ros-gz` for Gazebo Harmonic integration
- ✅ px4_msgs packages available

#### 3. Why Backend WITHOUT ROS2?
**Critical production requirement**: Backend must be deployable to cloud/production without ROS2 dependencies.

**Architecture**: Separate concerns via bridge service
```
Backend (FastAPI)
    ↕ HTTP/WebSocket
ROS2 Bridge Service (future)
    ↕ ROS2 Topics
MAVROS + Simulation
```

**Benefits**:
- ✅ Standard web stack (portable to any cloud)
- ✅ Lightweight (<200 MB vs >3 GB with ROS2)
- ✅ No DDS networking complexity in production
- ✅ Standard deployment practices (Docker, K8s)
- ✅ Team members can work on backend without ROS2 knowledge

---

## Component Dependencies
### Simulation Container Dependencies
**Build-time**:
- Ubuntu 22.04 base image
- ROS2 Humble (`ros-humble-ros-base`)
- Gazebo Harmonic (`gz-harmonic`, `libgz-sim8-dev`)
- OpenCV (`libopencv-dev`) - Required for Gazebo camera plugins
- GStreamer (`libgstreamer1.0-dev`) - Video streaming simulation
- PX4 v1.16.0 source + submodules
- Python packages (empy, jinja2, numpy, pymavlink)

**Runtime**:
- gz sim process (Gazebo Harmonic simulation engine)
- px4 process (SITL firmware)
- X11 display (optional, for GUI)

**Exposes**: MAVLink on UDP port 14540 (localhost only, network_mode: host)

### ROS2 Core Container Dependencies
**Build-time**:
- osrf/ros:humble-desktop-full-jammy base
- MAVROS packages (`ros-humble-mavros`, `ros-humble-mavros-extras`)
- Gazebo ROS integration (`ros-humble-ros-gz`)
- Gazebo Harmonic (`gz-harmonic`)
- Geographic datasets (for MAVROS GPS conversion)
- Custom ROS2 workspace with `mavros_launcher` package

**Runtime**:
- ROS2 DDS daemon
- mavros_node process (MAVLink ↔ ROS2 bridge)
- FastDDS configuration (custom multicast settings)

**Depends on**:
- simulation container (healthcheck: gz sim + px4 running)
- ROS_DOMAIN_ID=42 (must match across containers)

**Exposes**: ROS2 topics on DDS multicast (requires network_mode: host)

### Backend Container Dependencies
**Build-time**:
- python:3.10-slim base
- FastAPI + Uvicorn
- Pydantic (data validation)
- SQLAlchemy + aiosqlite (database)

**Runtime**:
- uvicorn ASGI server
- SQLite database (volume mounted)

**Depends on**: None (independent, communicates via future bridge service)

**Exposes**: HTTP API on port 8000

---

## Data Flow Example
**Scenario**: Send drone to waypoint (10, 20, 5 meters)

1. **Frontend** → `POST /missions` → **Backend** (HTTP)
2. **Backend** stores mission → Database (SQLite)
3. **(Future) Backend** → Bridge Service → ROS2 topic `/missions/new`
4. **Custom ROS2 Node** subscribes → Converts to setpoint
5. **Node** publishes → `/drone_0/mavros/setpoint_position/local`
6. **MAVROS** receives ROS2 message → Converts to MAVLink
7. **MAVROS** sends → `SET_POSITION_TARGET_LOCAL_NED` via UDP:14540
8. **PX4 SITL** receives MAVLink → Navigator module processes
9. **PX4** calculates trajectory → Motor PWM commands
10. **Gazebo Plugin** receives PWM → Applies physics forces
11. **Gazebo** updates → Drone position changes
12. **Simulated GPS** → Position data back to PX4
13. **PX4** → `GLOBAL_POSITION_INT` MAVLink message
14. **MAVROS** receives → Publishes `/drone_0/mavros/local_position/pose`
15. **(Future) Bridge** subscribes → Forwards to Backend via HTTP
16. **Backend** → WebSocket → **Frontend** (real-time update)

**Round-trip latency**: ~50-100ms (simulation + ROS2 + HTTP)

---

## Project Structure
```
artefac-drone-defense/
├── .claude/                    # Claude Code configuration
│   └── plan/
│       └── architecture-dockerize.md   # Detailed implementation plan
├── backend/
│   ├── app/
│   │   └── main.py            # FastAPI application
│   ├── Dockerfile              # Python 3.10 slim
│   └── requirements.txt
├── simulation/
│   ├── src/
│   │   ├── mavros_launcher/    # ROS2 package for MAVROS
│   │   │   ├── launch/
│   │   │   │   └── px4_sitl.launch.py
│   │   │   ├── package.xml
│   │   │   └── CMakeLists.txt
│   │   └── README.md
│   ├── config/
│   │   └── fastdds.xml         # DDS configuration
│   ├── gazebo_worlds/          # Custom Gazebo world files
│   ├── models/                 # Gazebo model definitions
│   ├── Dockerfile              # ROS2 Humble + MAVROS
│   └── Dockerfile.px4          # PX4 v1.16.0 build
├── logs/                       # Container logs (gitignored)
│   ├── px4/
│   ├── ros2/
│   └── backend/
├── docker-compose.yml          # Service orchestration
├── .env.example                # Environment variables template
├── CLAUDE.md                   # Development guidelines
└── README.md                   # This file
```

---

## Contact
**Team**: Evolutek<<  
**Email**: evolutek.ionis@gmail.com  
**Challenge**: 4 - Livraison en Situation de Crise  
**Event**: Hackathon Artefac Drone Defense  
