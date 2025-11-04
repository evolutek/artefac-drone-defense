# Architecture Complète - Artefac Drone Defense

## Vue d'Ensemble Globale

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            ENVIRONNEMENT DE DÉVELOPPEMENT                           │
│                                  (Docker Compose)                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────┐         ┌────────────────────────────────────────────────┐
│  SIMULATION LAYER      │         │         MIDDLEWARE LAYER (ROS2)                │
│  (Disappears in Prod)  │         │         (Evolves in Production)                │
├────────────────────────┤         ├────────────────────────────────────────────────┤
│                        │         │                                                │
│  Container: simulation │         │  Container: ros2_core                          │
│  ┌──────────────────┐  │         │  ┌──────────────────────────────────────────┐  │
│  │  PX4 Autopilot   │  │         │  │                                          │  │
│  │  v1.16.0 (SITL)  │  │         │  │  ┌────────────┐    ┌──────────────┐      │  │
│  │                  │  │MAVLink  │  │  │  MAVROS    │    │ MQTT Bridge  │      │  │
│  │  Drone 1: 4560 ──┼──┼────────>│  │  │  Node      │───>│   Node       │      │  │
│  │  Drone 2: 4561 ──┼──┼────────>│  │  │            │    │              │      │  │
│  │  Drone N: 456N ──┼──┼────────>│  │  │  Topics:   │    │  Publishes:  │      │  │
│  │                  │  │  TCP    │  │  │  /drone_1/ │    │  telemetry/  │      │  │
│  └────────┬─────────┘  │         │  │  │  /drone_2/ │    │  drone_N/*   │      │  │
│           │            │         │  │  │  /mavros/* │    │              │      │  │
│  ┌────────▼─────────┐  │         │  │  └──────┬─────┘    └──────┬───────┘      │  │
│  │ Gazebo Harmonic  │  │         │  │         │                 │              │  │
│  │  Physics Engine  │  │         │  │  ┌──────▼─────────────────▼─────────┐    │  │
│  │                  │  │         │  │  │     ROS2 DDS Network             │    │  │
│  │  World: Toulouse │  │         │  │  │  (FastRTPS with custom profile)  │    │  │
│  │  Models: X500    │  │         │  │  │  Domain ID: 42                   │    │  │
│  │  Sensors: GPS,   │  │         │  │  └──────────────────▲───────────────┘    │  │
│  │  IMU, Camera     │  │         │  │                     │                    │  │
│  └──────────────────┘  │         │  └─────────────────────┼────────────────────┘  │
│                        │         │                        │                       │
│  Ports: 14540-14580    │         │  network_mode: host    │                       │
│  GUI: X11 forwarding   │         │  ROS_DOMAIN_ID: 42     │                       │
└────────────────────────┘         └────────────────────────┼───────────────────────┘
                                                            │
                                                            │ MQTT Protocol
                                                            │
        ┌───────────────────────────────────────────────────▼────────────────────────┐
        │                    COMMUNICATION LAYER                                     │
        │                    (Stays in Production)                                   │
        ├────────────────────────────────────────────────────────────────────────────┤
        │                                                                            │
        │  Container: mqtt                                                           │
        │  ┌──────────────────────────────────────────────────────────────────────┐  │
        │  │  Eclipse Mosquitto 2.0 (MQTT Broker)                                 │  │
        │  │                                                                      │  │
        │  │  Topics:                                                             │  │
        │  │    telemetry/drone_N/gps         ← ros2_core publishes               │  │
        │  │    telemetry/drone_N/battery     ← ros2_core publishes               │  │
        │  │    telemetry/drone_N/state       ← ros2_core publishes               │  │
        │  │    commands/drone_N/goto         ← backend publishes                 │  │
        │  │    commands/drone_N/arm          ← backend publishes                 │  │
        │  │    commands/drone_N/mission      ← backend publishes                 │  │
        │  │                                                                      │  │
        │  │  Ports: 1883 (MQTT), 9001 (WebSocket)                                │  │
        │  │  QoS: 0 (telemetry), 1 (commands), 2 (critical)                      │  │
        │  └───────────────────┬──────────────────────────────────────────────────┘  │
        │                      │                                                     │
        └──────────────────────┼─────────────────────────────────────────────────────┘
                               │
                               │ MQTT Subscribe/Publish
                               │
        ┌──────────────────────▼─────────────────────────────────────────────────────┐
        │                    APPLICATION LAYER                                       │
        │                    (Stays in Production)                                   │
        ├────────────────────────────────────────────────────────────────────────────┤
        │                                                                            │
        │  Container: backend                      Container: frontend               │
        │  ┌────────────────────────────┐         ┌──────────────────────────────┐   │
        │  │  FastAPI Application       │         │  React + Vite + Nginx        │   │
        │  │  (Pure Python, no ROS2)    │         │  (Static Web App)            │   │
        │  │                            │  HTTP   │                              │   │
        │  │  ┌──────────────────────┐  │ <──────>│  ┌────────────────────────┐  │   │
        │  │  │  REST API            │  │         │  │  Web Interface         │  │   │
        │  │  │  - Missions CRUD     │  │         │  │  - Map Viewer          │  │   │
        │  │  │  - Fleet Management  │  │         │  │  - Mission Planner     │  │   │
        │  │  │  - User Auth         │  │         │  │  - Drone Status        │  │   │
        │  │  └──────────────────────┘  │         │  │  - Video Streams       │  │   │
        │  │                            │         │  └────────────────────────┘  │   │
        │  │  ┌──────────────────────┐  │ WebSocket                              │   │
        │  │  │  WebSocket Server    │  │ <──────>│                              │   |
        │  │  │  - Real-time updates │  │         │  Real-time telemetry         │   │
        │  │  └──────────────────────┘  │         │                              │   │
        │  │                            │         │  Port: 3000 → 80 (nginx)     │   │
        │  │  ┌──────────────────────┐  │         └──────────────────────────────┘   │
        │  │  │  MQTT Client         │  │                                            │
        │  │  │  - Subscribe: telemetry |                                            │
        │  │  │  - Publish: commands │  │                                            │
        │  │  └──────────┬───────────┘  │                                            │
        │  │             │              │                                            │
        │  │  ┌──────────▼───────────┐  │                                            │
        │  │  │  Database (SQLite)   │  │                                            │
        │  │  │  - Missions          │  │                                            │
        │  │  │  - Users             │  │                                            │
        │  │  │  - Logs              │  │                                            │
        │  │  │  - Drone Registry    │  │                                            │
        │  │  └──────────────────────┘  │                                            │
        │  │                            │                                            │
        │  │  Port: 8000                │                                            │
        │  └────────────────────────────┘                                            │
        │                                                                            │
        └────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            PERSISTENT STORAGE (Docker Volumes)                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  px4_build       │  ros2_install  │  ros2_build  │  backend_data │  mqtt_data       │
│  (build cache)   │  (ROS2 pkgs)   │  (colcon)    │  (SQLite DB)  │  (retained msgs) │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Description Détaillée par Couche

### 1. SIMULATION LAYER (Development Only)

#### Container: `simulation`
**Image**: Custom (`simulation/Dockerfile.px4`)
**Base**: Ubuntu 22.04 + ROS2 Humble + Gazebo Harmonic

**Composants principaux:**

##### A. PX4 Autopilot (SITL Mode)
- **Version**: v1.16.0 (latest stable avec support Gazebo Harmonic)
- **Mode**: Software-In-The-Loop (firmware simulé en espace utilisateur)
- **Processus**: Un processus `px4` par drone simulé
- **Ports MAVLink**:
  - Drone 1: TCP 4560 (protocol v2.0)
  - Drone 2: TCP 4561
  - Drone N: TCP 4560 + (N-1)
- **Protocoles exposés**:
  - MAVLink v2.0 (commandes flight controller)
  - UDP 18570+ (Gazebo Bridge)

**Fonctionnalités simulées:**
- Flight modes (MANUAL, STABILIZED, POSITION, MISSION, RTL)
- Failsafes (battery, RC loss, GPS loss)
- Arming checks
- Parameter system (500+ params)
- Mission protocol (waypoints, rally points)

##### B. Gazebo Harmonic (gz sim)
- **Version**: Harmonic (LTS until September 2027)
- **Rôle**: Simulation physique et sensorielle
- **Monde par défaut**: Toulouse (43.6047°N, 1.4442°E)
- **Modèles disponibles**:
  - `gz_x500`: Quadcopter standard (choix par défaut)
  - `gz_x500_depth`: Avec caméra de profondeur
  - `gz_rc_cessna`: Fixed-wing

**Capteurs simulés:**
- GPS (NMEA avec bruit configurable)
- IMU (accéléromètre + gyroscope, 100Hz)
- Magnétomètre (heading)
- Baromètre (altitude)
- Optical Flow (positionnement indoor)
- Caméras RGB/Depth (optionnel)
- Lidar 2D/3D (optionnel)

**Physics Engine:**
- Moteur: DART (par défaut) ou Bullet
- Real-time factor: 1.0 (temps réel) ou rapide (simulations batch)
- Aérodynamique: Modèle blade element pour props
- Collision detection: Mesh-based

**Environment Variables:**
```bash
GZ_SIM_RESOURCE_PATH=/root/PX4-Autopilot/Tools/simulation/gz/models:/root/.gz/sim/models
GZ_SIM_SYSTEM_PLUGIN_PATH=/root/PX4-Autopilot/build/px4_sitl_default/build_gz
DISPLAY=:0  # X11 forwarding pour GUI
HEADLESS=0  # 0=GUI, 1=headless (CI/CD)
```

**Interaction PX4 ↔ Gazebo:**
```
PX4 SITL Process
    ↓ [écrit commandes moteurs via UDP]
Gazebo Plugin (gz-px4-interface)
    ↓ [simule physique]
Gazebo Physics Engine
    ↓ [retourne état capteurs via UDP]
PX4 SITL Process [boucle fermée]
```

**Volumes montés:**
- `/tmp/.X11-unix`: GUI rendering
- `./simulation/gazebo_worlds`: Mondes custom
- `./simulation/models`: Modèles custom
- `px4_build`: Cache de compilation (~2GB)

**Healthcheck:**
```bash
ps aux | grep 'gz sim' && ps aux | grep px4
# Vérifie que les deux processus sont actifs
```

**Limites de performance:**
- CPU: ~15% par drone (Intel i7)
- GPU: Requis si rendering activé (Nvidia recommandé)
- Max drones simultanés: ~10 (bottleneck GPU)

**🔴 PRODUCTION: Ce conteneur disparaît complètement**
Remplacé par des drones physiques avec autopilote Pixhawk.

---

### 2. MIDDLEWARE LAYER (Evolves in Production)

#### Container: `ros2_core`
**Image**: Custom (`simulation/Dockerfile`)
**Base**: osrf/ros:humble-desktop-full

**Rôle**: Pont de traduction entre protocoles drone et cloud

**Composants principaux:**

##### A. MAVROS (MAVLink ↔ ROS2 Bridge)
- **Package**: ros-humble-mavros + mavros-extras
- **Version**: 2.6.0+ (ROS2 Humble)
- **Protocole**: MAVLink v2.0 (micro air vehicle link)

**Architecture MAVROS:**
```
PX4/Drone ──[MAVLink]──> MAVROS Node ──[ROS2 Topics]──> Applications
                              ↕
                        Plugin System
                    (30+ plugins chargés dynamiquement)
```

**Plugins activés (voir `px4_sitl.launch.py:59-72`):**

| Plugin | Topics ROS2 | Fonction |
|--------|-------------|----------|
| `sys_status` | `/mavros/state` | État connexion, mode vol, armé |
| `sys_time` | `/mavros/time_reference` | Synchro horloge FCU |
| `imu` | `/mavros/imu/data` | Accéléro + gyro + orientation |
| `local_position` | `/mavros/local_position/pose` | Position locale (ENU frame) |
| `global_position` | `/mavros/global_position/global` | GPS (lat/lon/alt WGS84) |
| `command` | `/mavros/cmd/*` | Arm, takeoff, land, velocity |
| `battery` | `/mavros/battery` | Voltage, current, remaining % |
| `rc` | `/mavros/rc/in` | Télécommande RC |
| `param` | `/mavros/param/*` | Lecture/écriture params PX4 |
| `mission` | `/mavros/mission/*` | Upload/download waypoints |
| `home_position` | `/mavros/home_position/home` | Point de départ RTL |

**Configuration multi-drone:**
```python
# Chaque drone a son propre namespace
namespace='/drone_1'  # Topics: /drone_1/mavros/state
namespace='/drone_2'  # Topics: /drone_2/mavros/state

# System IDs uniques
tgt_system=1  # Drone 1
tgt_system=2  # Drone 2
```

**URL de connexion:**
- **Simulation**: `tcp://127.0.0.1:4560` (localhost)
- **Production Serial**: `/dev/ttyUSB0:921600` (FTDI vers Pixhawk)
- **Production WiFi**: `udp://:14540@192.168.1.42:14557`

**Frame Transforms (TF):**
```
map (global frame)
 └─> base_link (drone body frame)
      └─> camera_link (sensors)
```

##### B. MQTT Bridge Node
- **Package custom**: `mqtt_bridge` (à développer)
- **Langage**: Python 3.10 avec `rclpy` + `paho-mqtt`

**Fonction**: Traduit ROS2 Topics → MQTT Topics

**Mapping des topics:**
```python
# ROS2 → MQTT (telemetry)
/drone_1/mavros/state                → mqtt://telemetry/drone_1/state
/drone_1/mavros/global_position/global → mqtt://telemetry/drone_1/gps
/drone_1/mavros/battery              → mqtt://telemetry/drone_1/battery

# MQTT → ROS2 (commands)
mqtt://commands/drone_1/goto         → /drone_1/mavros/setpoint_position/global
mqtt://commands/drone_1/arm          → /drone_1/mavros/cmd/arming
mqtt://commands/drone_1/mission      → /drone_1/mavros/mission/push
```

**QoS Configuration:**
```python
# ROS2 QoS (pour DDS)
qos_profile = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10
)

# MQTT QoS
telemetry_qos = 0  # Best effort (high frequency data)
command_qos = 1    # At least once (critical commands)
```

##### C. ROS2 DDS Network (FastRTPS)
- **Implémentation**: rmw_fastrtps_cpp (eProsima Fast DDS)
- **Alternative**: CycloneDDS (meilleur pour WAN)

**Configuration custom (`fastdds.xml`):**
```xml
<!-- Buffer sizes optimisés pour multi-drone -->
<sendBufferSize>1048576</sendBufferSize>      <!-- 1MB -->
<receiveBufferSize>4194304</receiveBufferSize> <!-- 4MB -->
<maxMessageSize>65500</maxMessageSize>         <!-- 64KB -->
```

**Discovery Protocol:**
- **SIMPLE**: Multicast UDP pour découverte automatique
- **Lease Duration**: 10s (détection perte de connexion)
- **Domain ID**: 42 (isolement réseau)

**Network Requirements:**
- `network_mode: host` obligatoire (multicast DDS)
- Ports utilisés: UDP 7400-7500 (discovery + data)

**🟢 PRODUCTION: Conteneur transformé**

**Ce qui reste:**
- MAVROS (connexion drone réel)
- MQTT Bridge (même code)
- ROS2 Core (topic routing)

**Ce qui disparaît:**
- `ros_gz` packages (pas de simulation)
- Tools de debug (rqt, rviz)
- Desktop packages (libère 500MB)

**Deux stratégies de déploiement:**

**Option A - Centralisée (Ground Station):**
```
Serveur Kubernetes
┌─────────────────────────────┐
│  Pod: ros2-orchestrator     │
│  ┌────────┐  ┌────────┐     │
│  │MAVROS 1│  │MAVROS 2│ ... │
│  └───┬────┘  └───┬────┘     │
└──────┼───────────┼──────────┘
       │WiFi       │WiFi
   ┌───▼───┐   ┌───▼───┐
   │Drone 1│   │Drone 2│
   └───────┘   └───────┘
```

**Option B - Distribuée (Onboard):**
```
Drone 1                  Drone 2
┌─────────────────┐     ┌─────────────────┐
│ Raspberry Pi 4  │     │ Jetson Nano     │
│ ros2_agent      │     │ ros2_agent      │
│ └> MAVROS       │     │ └> MAVROS       │
│    └> Pixhawk   │     │    └> Pixhawk   │
└─────────────────┘     └─────────────────┘
```

---

### 3. COMMUNICATION LAYER (Production Ready)

#### Container: `mqtt`
**Image**: eclipse-mosquitto:2.0
**Type**: Message Broker (Pub/Sub)

**Rôle**: Hub de communication asynchrone découplé

**Architecture Pub/Sub:**
```
Publisher                    Broker                Subscriber
ros2_core ──publish──> [Topic: telemetry/drone_1/gps] ──subscribe──> backend
backend   ──publish──> [Topic: commands/drone_1/goto] ──subscribe──> ros2_core
```

**Topics utilisés:**

**Télémétrie (ros2 → backend):**
```
telemetry/drone_N/state
  Payload: {"mode": "OFFBOARD", "armed": true, "connected": true}
  QoS: 0 (best effort)
  Frequency: 1Hz

telemetry/drone_N/gps
  Payload: {"lat": 43.6047, "lon": 1.4442, "alt": 125.3, "hdop": 0.8}
  QoS: 0
  Frequency: 5Hz

telemetry/drone_N/battery
  Payload: {"voltage": 16.4, "current": 8.2, "remaining": 75}
  QoS: 0
  Frequency: 1Hz

telemetry/drone_N/local_position
  Payload: {"x": 10.2, "y": -5.4, "z": 15.0, "vx": 2.1, "vy": 0.5, "vz": 0.1}
  QoS: 0
  Frequency: 10Hz
```

**Commandes (backend → ros2):**
```
commands/drone_N/arm
  Payload: {"arm": true}
  QoS: 1 (at least once)

commands/drone_N/takeoff
  Payload: {"altitude": 10.0}
  QoS: 1

commands/drone_N/goto
  Payload: {"lat": 43.605, "lon": 1.445, "alt": 50.0, "yaw": 90}
  QoS: 1

commands/drone_N/mission
  Payload: {"waypoints": [...], "action": "upload"}
  QoS: 1

commands/drone_N/rtl
  Payload: {}
  QoS: 1
```

**Configuration Mosquitto:**
```conf
# mosquitto.conf (dev)
listener 1883 0.0.0.0
protocol mqtt

listener 9001 0.0.0.0
protocol websockets

allow_anonymous true
```

**Production hardening:**
```conf
# mosquitto.conf (prod)
listener 8883
protocol mqtt
cafile /certs/ca.crt
certfile /certs/server.crt
keyfile /certs/server.key

password_file /mosquitto/config/passwd
acl_file /mosquitto/config/acl

max_connections 1000
max_queued_messages 10000
```

**ACL Example (production):**
```
# Backend users can publish commands
user backend_service
topic write commands/#

# ROS2 bridge can publish telemetry
user ros2_bridge
topic write telemetry/#
topic read commands/#

# Frontend read-only telemetry
user frontend_client
topic read telemetry/#
```

**Retained Messages:**
- Last telemetry retained (nouveaux clients reçoivent dernière valeur)
- Commands NOT retained (éviter commandes obsolètes)

**Persistence:**
- Messages persistés sur volume `mqtt_data`
- QoS 1/2 messages sauvés sur disque
- Survit aux redémarrages

**Monitoring:**
```bash
# System topics (stats internes)
$SYS/broker/clients/connected
$SYS/broker/messages/received
$SYS/broker/uptime
```

**Healthcheck:**
```bash
mosquitto_sub -t '$SYS/#' -C 1 -i healthcheck -W 3
# Subscribe à un message système avec timeout 3s
```

**🟢 PRODUCTION: Reste identique ou remplacé**

**Options:**
1. **Self-hosted**: Même conteneur avec TLS + auth
2. **Managed Services**:
   - **AWS IoT Core**: Intégration native avec AWS services
   - **Azure IoT Hub**: Integration avec Azure ecosystem
   - **HiveMQ Cloud**: Scalable MQTT cluster
   - **CloudMQTT**: Managed Mosquitto

**Avantages managed service:**
- HA automatique (99.9% SLA)
- Scaling transparent
- Monitoring intégré (CloudWatch, etc.)
- Device registry
- Certificats X.509 automatiques

---

### 4. APPLICATION LAYER (Production Ready)

#### Container: `backend`
**Image**: Custom (`backend/Dockerfile`)
**Base**: python:3.10-slim

**Rôle**: API métier et orchestration de flotte

##### A. FastAPI Application

**Structure du code:**
```
backend/app/
├── main.py              # Application entry point
├── models/              # SQLAlchemy ORM models
│   ├── mission.py
│   ├── drone.py
│   └── user.py
├── schemas.py           # Pydantic schemas (validation)
├── crud/                # Database operations
│   ├── missions.py
│   └── drones.py
├── mqtt_client.py       # MQTT async client
├── websocket_manager.py # WebSocket connections pool
└── routers/             # API endpoints
    ├── missions.py
    ├── drones.py
    └── users.py
```

**Endpoints principaux:**

**Missions Management:**
```python
POST   /api/missions/          # Create new mission
GET    /api/missions/          # List all missions
GET    /api/missions/{id}      # Get mission details
PUT    /api/missions/{id}      # Update mission
DELETE /api/missions/{id}      # Delete mission
POST   /api/missions/{id}/start # Deploy to drone(s)
```

**Fleet Management:**
```python
GET    /api/drones/            # List active drones
GET    /api/drones/{id}        # Get drone status
POST   /api/drones/{id}/command # Send command (arm, takeoff, goto, rtl)
GET    /api/drones/{id}/telemetry # Historical telemetry
```

**Authentication:**
```python
POST   /api/auth/login         # JWT token generation
POST   /api/auth/register      # User registration
GET    /api/auth/me            # Current user info
```

**WebSocket (Real-time):**
```python
WS     /ws/telemetry           # Stream all drones telemetry
WS     /ws/drone/{id}          # Stream single drone
```

##### B. MQTT Client Integration

**Async MQTT avec paho-mqtt:**
```python
# mqtt_client.py
class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client(client_id="backend_service")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        # Subscribe to all telemetry
        client.subscribe("telemetry/#")

    def _on_message(self, client, userdata, msg):
        # Parse telemetry and store in DB
        topic = msg.topic  # e.g., "telemetry/drone_1/gps"
        payload = json.loads(msg.payload)

        # Update in-memory cache
        self.telemetry_cache[topic] = payload

        # Broadcast to WebSocket clients
        websocket_manager.broadcast(payload)

    def publish_command(self, drone_id, command, payload):
        topic = f"commands/{drone_id}/{command}"
        self.client.publish(topic, json.dumps(payload), qos=1)
```

**Flow example (Mission Start):**
```
User clicks "Start Mission" in UI
    ↓
Frontend → POST /api/missions/42/start
    ↓
Backend FastAPI → Validates mission
    ↓
Backend → MQTT publish to "commands/drone_1/mission"
    ↓
MQTT Broker → ros2_core subscribes
    ↓
MQTT Bridge → ROS2 topic /drone_1/mavros/mission/push
    ↓
MAVROS → MAVLink MISSION_ITEM messages
    ↓
PX4 Autopilot → Mission loaded
```

##### C. Database (SQLite → PostgreSQL)

**Models:**

**Drone Model:**
```python
class Drone(Base):
    id = Column(String, primary_key=True)  # "drone_1"
    name = Column(String)
    model = Column(String)  # "X500", "Cessna"
    last_seen = Column(DateTime)
    status = Column(Enum("connected", "disconnected", "error"))
    current_mission_id = Column(Integer, ForeignKey("missions.id"))
```

**Mission Model:**
```python
class Mission(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    waypoints = Column(JSON)  # List of {lat, lon, alt, action}
    assigned_drones = Column(JSON)  # ["drone_1", "drone_2"]
    status = Column(Enum("draft", "running", "completed", "failed"))
    created_at = Column(DateTime)
```

**Telemetry Log Model:**
```python
class TelemetryLog(Base):
    id = Column(Integer, primary_key=True)
    drone_id = Column(String, ForeignKey("drones.id"))
    timestamp = Column(DateTime)
    position = Column(JSON)  # {lat, lon, alt}
    battery = Column(Float)
    mode = Column(String)
```

**Migration to PostgreSQL (production):**
```python
# .env (dev)
DATABASE_URL=sqlite:///./backend_data/app.db

# .env (prod)
DATABASE_URL=postgresql://user:pass@postgres:5432/artefac_db
```

##### D. WebSocket Real-time Updates

**Architecture:**
```
Backend maintains pool of WebSocket connections
    ↓
On MQTT message received:
    ↓
websocket_manager.broadcast(data)
    ↓
All connected frontend clients receive update
```

**Implementation:**
```python
# websocket_manager.py
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)
```

**Frontend usage:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/telemetry');
ws.onmessage = (event) => {
    const telemetry = JSON.parse(event.data);
    updateDroneMarker(telemetry.drone_id, telemetry.position);
};
```

**🟢 PRODUCTION: Scaling Strategy**

**Horizontal Scaling (Kubernetes):**
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 3  # 3 instances
  template:
    spec:
      containers:
      - name: backend
        image: evolutek/backend:v1.0.0
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
```

**Load Balancing:**
- Nginx/Traefik pour HTTP
- Sticky sessions pour WebSocket (même pod)
- Redis pour session sharing

**Monitoring:**
- Prometheus metrics (`/metrics` endpoint)
- Sentry error tracking
- Structured logging (JSON)

---

#### Container: `frontend`
**Image**: Custom (`frontend/Dockerfile`)
**Base**: node:18 (build) → nginx:alpine (runtime)

**Rôle**: Interface utilisateur web

##### A. React Application (assumed stack)

**Structure:**
```
frontend/src/
├── components/
│   ├── Map.tsx              # Leaflet/Mapbox map viewer
│   ├── DroneMarker.tsx      # Drone icon with heading
│   ├── MissionPlanner.tsx   # Waypoint editor
│   └── TelemetryPanel.tsx   # Real-time status
├── pages/
│   ├── Dashboard.tsx        # Fleet overview
│   ├── MissionEditor.tsx    # Create missions
│   └── DroneDetail.tsx      # Single drone view
├── hooks/
│   ├── useWebSocket.ts      # WebSocket connection
│   └── useDroneTelemetry.ts # Real-time data
└── services/
    ├── api.ts               # Axios REST client
    └── websocket.ts         # WebSocket client
```

**Key Libraries (recommended):**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-leaflet": "^4.2.1",    // Map rendering
    "zustand": "^4.3.8",          // State management
    "axios": "^1.4.0",            // HTTP client
    "react-router-dom": "^6.11.2" // Routing
  }
}
```

##### B. Map Visualization

**Drone Marker Component:**
```typescript
// components/DroneMarker.tsx
interface DroneMarkerProps {
  position: [number, number]; // [lat, lon]
  heading: number;            // 0-360°
  status: 'connected' | 'disconnected' | 'error';
  battery: number;            // 0-100%
}

const DroneMarker: React.FC<DroneMarkerProps> = ({position, heading, status, battery}) => {
  const icon = L.divIcon({
    html: `
      <div style="transform: rotate(${heading}deg)">
        <svg><!-- Drone icon SVG --></svg>
        <span>${battery}%</span>
      </div>
    `,
    className: `drone-marker ${status}`
  });

  return <Marker position={position} icon={icon} />;
};
```

**Mission Planner:**
```typescript
// components/MissionPlanner.tsx
const MissionPlanner = () => {
  const [waypoints, setWaypoints] = useState<Waypoint[]>([]);

  const handleMapClick = (e: LeafletMouseEvent) => {
    setWaypoints([...waypoints, {
      lat: e.latlng.lat,
      lon: e.latlng.lng,
      alt: 50,  // Default altitude
      action: 'WAYPOINT'
    }]);
  };

  const saveMission = async () => {
    await api.post('/api/missions/', {
      name: 'Mission 1',
      waypoints: waypoints
    });
  };

  return (
    <MapContainer onClick={handleMapClick}>
      <Polyline positions={waypoints.map(w => [w.lat, w.lon])} />
    </MapContainer>
  );
};
```

##### C. Real-time Updates

**WebSocket Hook:**
```typescript
// hooks/useWebSocket.ts
const useWebSocket = (url: string) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    const ws = new WebSocket(url);

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setData(message);
    };

    return () => ws.close();
  }, [url]);

  return data;
};

// Usage in component
const telemetry = useWebSocket('ws://localhost:8000/ws/telemetry');
```

##### D. Production Build (Multi-stage Dockerfile)

```dockerfile
# Build stage
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build  # → dist/

# Runtime stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**Nginx Configuration:**
```nginx
server {
  listen 80;

  # React app
  location / {
    root /usr/share/nginx/html;
    try_files $uri /index.html;
  }

  # Proxy API calls
  location /api/ {
    proxy_pass http://backend:8000;
  }

  # WebSocket proxy
  location /ws/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }
}
```

**🟢 PRODUCTION: Optimizations**

**CDN Deployment:**
```
CloudFront (AWS) / Cloudflare
    ↓ [static assets: JS, CSS, images]
S3 Bucket / Object Storage
    ↓
User Browser (cached locally)
```

**Build Optimizations:**
- Code splitting (lazy loading routes)
- Tree shaking (remove unused code)
- Compression (gzip/brotli)
- Image optimization (WebP format)

---

### 5. PERSISTENT STORAGE

**Docker Volumes (Named):**

```yaml
volumes:
  px4_build:          # ~2GB - PX4 compilation artifacts
  ros2_install:       # ~500MB - ROS2 packages
  ros2_build:         # ~200MB - Colcon build output
  backend_data:       # ~100MB - SQLite database
  mqtt_data:          # ~10MB - Retained messages
  mqtt_logs:          # ~50MB - Broker logs
```

**Production Migration:**
- `backend_data`: SQLite → PostgreSQL (external service)
- `mqtt_data`: Persistent volume or managed service
- `px4_build`, `ros2_*`: Deleted (simulation removed)

---

## Data Flows Summary

### Telemetry Flow (Drone → UI)
```
Real Drone / Simulation
    ↓ [MAVLink v2.0 over TCP/Serial]
MAVROS Node (ros2_core)
    ↓ [ROS2 Topics via DDS]
MQTT Bridge Node (ros2_core)
    ↓ [MQTT Protocol]
Mosquitto Broker (mqtt)
    ↓ [MQTT Subscribe]
FastAPI Backend (backend)
    ↓ [WebSocket]
React Frontend (frontend)
    ↓ [DOM Update]
User sees drone position on map
```

### Command Flow (UI → Drone)
```
User clicks "Takeoff" button
    ↓ [HTTP POST /api/drones/drone_1/command]
FastAPI Backend
    ↓ [MQTT Publish to commands/drone_1/takeoff]
Mosquitto Broker
    ↓ [MQTT Subscribe]
MQTT Bridge Node (ros2_core)
    ↓ [ROS2 Service Call /drone_1/mavros/cmd/takeoff]
MAVROS Node
    ↓ [MAVLink COMMAND_LONG message]
PX4 Autopilot
    ↓ [Motor commands]
Drone takes off
```

---

## Performance Characteristics

| Metric | Development | Production |
|--------|-------------|------------|
| **Latency** | | |
| Sensor → UI | ~200ms | ~50ms (onboard) / ~300ms (WiFi) |
| Command → Action | ~150ms | ~80ms (onboard) / ~250ms (WiFi) |
| **Throughput** | | |
| Telemetry Rate | 10Hz per drone | 10Hz per drone |
| Max Drones | 10 (simulation limit) | 100 (centralized) / unlimited (distributed) |
| **Resources** | | |
| RAM per drone | ~500MB | ~100MB (agent only) |
| CPU per drone | ~15% (with sim) | ~5% (no sim) |
| Network | localhost | WiFi: 1Mbps/drone, 4G: 500kbps/drone |

---

## Security Considerations

### Development (Current)
- ❌ No authentication (MQTT allow_anonymous)
- ❌ No encryption (plain TCP)
- ❌ No authorization (all topics accessible)
- ✅ Network isolation (Docker bridge)

### Production (Required)
- ✅ MQTT: TLS + username/password + ACLs
- ✅ Backend: JWT tokens + HTTPS
- ✅ Frontend: httpOnly cookies + CSP headers
- ✅ ROS2: SROS2 (encrypted DDS)
- ✅ Firewall: Whitelist only required ports

---

## Deployment Evolution

### Current (docker-compose)
```bash
docker compose up
# All services on single machine
```

### Production Option 1: Docker Swarm
```bash
docker stack deploy -c docker-compose.prod.yml artefac
# Multi-host orchestration
```

### Production Option 2: Kubernetes
```bash
kubectl apply -f k8s/
# Deployment, Service, Ingress, ConfigMaps
```

### Production Option 3: Cloud Native
```
AWS ECS (backend containers)
+ AWS IoT Core (MQTT)
+ AWS RDS (PostgreSQL)
+ CloudFront (frontend CDN)
+ EC2 (ros2_core on ground station)
```

---

## Next Steps for Scalability

1. **Implement Swarm Manager** (dynamic drone discovery)
2. **Replace SQLite with PostgreSQL** (multi-instance backend)
3. **Add Redis** (session sharing + caching)
4. **Implement MQTT auth** (security)
5. **Add Prometheus** (monitoring)
6. **CI/CD Pipeline** (automated deployment)

