# Simulation vs Production - Architecture Comparée

**Date**: 2025-11-16
**Objectif**: Comprendre comment le système évolue de la simulation Docker vers les drones réels
**Audience**: Développeurs, équipe technique, partenaires

---

## Vue d'Ensemble Rapide

| Aspect | **Simulation** | **Production** |
|--------|----------------|----------------|
| **ROS2** | Container Docker sur PC dev | **Raspberry Pi embarqué sur drone** |
| **Autopilote** | PX4 SITL (logiciel) | **Pixhawk 6C (hardware MCU)** |
| **Physique** | Gazebo Harmonic | **Monde réel** |
| **Vision** | Ground truth Gazebo | **Intel RealSense T265 (caméra USB)** |
| **Communication PX4** | UDP localhost:14540 | **UART /dev/ttyUSB0:57600** |
| **MQTT** | Container local | **Broker cloud (WiFi/4G)** |
| **Code ROS2** | ✅ Identique à 95% | ✅ **Identique à 95%** |

**Point Clé**: ROS2 ne disparaît PAS en production ! Il tourne sur un ordinateur embarqué (Raspberry Pi) à bord du drone.

---

## 1. Architecture Simulation (Développement)

```
┌─────────────────────────────────────────────────────────┐
│        MACHINE DE DÉVELOPPEMENT (Linux/macOS)           │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Container: simulation                            │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Gazebo Harmonic (Moteur Physique)          │  │  │
│  │  │  - Simule gravité, aérodynamique, collisions│  │  │
│  │  │  - World: Toulouse (lat/lon configurable)   │  │  │
│  │  │  - Modèles: x500_0, x500_1 (quadcopters)    │  │  │
│  │  └─────────────────┬───────────────────────────┘  │  │
│  │                    │ Gazebo Transport (IPC/TCP)    │  │
│  │  ┌─────────────────▼───────────────────────────┐  │  │
│  │  │  PX4 Autopilot v1.16.0 SITL                 │  │  │
│  │  │  - Firmware identique au Pixhawk réel       │  │  │
│  │  │  - Reçoit: IMU, Baro, Mag depuis Gazebo     │  │  │
│  │  │  - Envoie: Commandes moteurs → Gazebo       │  │  │
│  │  │  - MAVLink UDP port 14540                   │  │  │
│  │  └─────────────────┬───────────────────────────┘  │  │
│  └────────────────────┼───────────────────────────────┘  │
│                       │ MAVLink UDP (localhost)          │
│  ┌────────────────────▼───────────────────────────────┐  │
│  │  Container: ros2_integration                      │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │  MAVROS (MAVLink → ROS2 Bridge)              │ │  │
│  │  │  - Topics: /mavros/state, /mavros/local_*   │ │  │
│  │  │  - Services: arming, takeoff, land           │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │  vision_pose_bridge                          │ │  │
│  │  │  - Lit: /model/x500_0/odometry (Gazebo)      │ │  │
│  │  │  - Publie: /mavros/odometry/out → PX4 EKF2  │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │  mqtt_bridge                                 │ │  │
│  │  │  - Souscrit: topics MAVROS                   │ │  │
│  │  │  - Publie: MQTT drone/{id}/telemetry         │ │  │
│  │  └────────────────┬─────────────────────────────┘ │  │
│  └───────────────────┼───────────────────────────────┘  │
│                      │ MQTT (localhost)                 │
│  ┌───────────────────▼───────────────────────────────┐  │
│  │  Container: mqtt (Mosquitto)                      │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │                                  │
│  ┌───────────────────▼───────────────────────────────┐  │
│  │  Container: backend (FastAPI)                     │  │
│  │  Container: frontend (React)                      │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

Latence PX4↔ROS2: <1 ms
Latence ROS2↔Backend: <1 ms
CPU: ~30-40% (8-core)
RAM: ~6 GB
```

---

## 2. Architecture Production (Drone Réel)

```
┌─────────────────────────────────────────────────────────┐
│                    DRONE PHYSIQUE                       │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Pixhawk 6C (Autopilote Hardware)                │  │
│  │  ┌─────────────────────────────────────────────┐ │  │
│  │  │  MCU: STM32H7 (480 MHz ARM Cortex-M7)       │ │  │
│  │  │  PX4 Firmware v1.16.0 (même version!)       │ │  │
│  │  │  - IMU: ICM-42688-P (400 Hz)                │ │  │
│  │  │  - Barometer: ICP-20100 (50 Hz)             │ │  │
│  │  │  - Magnetometer: BMM150 (100 Hz)            │ │  │
│  │  │  - ESC: Contrôle 4 moteurs brushless        │ │  │
│  │  └─────────────────┬───────────────────────────┘ │  │
│  └────────────────────┼─────────────────────────────┘  │
│                       │ MAVLink UART /dev/ttyUSB0       │
│                       │ (57600 bauds, câble physique)   │
│  ┌────────────────────▼─────────────────────────────┐   │
│  │  Raspberry Pi 4 (Companion Computer Embarqué)   │   │
│  │  ┌────────────────────────────────────────────┐ │   │
│  │  │  Ubuntu 22.04 Server ARM64                 │ │   │
│  │  │  ROS2 Humble                               │ │   │
│  │  │  CPU: ARM Cortex-A72 quad-core @ 1.5 GHz  │ │   │
│  │  │  RAM: 4 GB                                 │ │   │
│  │  │  Power: 5V @ 3A (via BEC batterie drone)  │ │   │
│  │  └────────────────────────────────────────────┘ │   │
│  │                                                 │   │
│  │  ┌──────────────────────────────────────────┐   │   │
│  │  │  MAVROS (MAVLink UART → ROS2)            │   │   │
│  │  │  ← MÊME CODE QU'EN SIMULATION!           │   │   │
│  │  │  Topics: /mavros/state, /mavros/local_*  │   │   │
│  │  │  Services: arming, takeoff, land          │   │   │
│  │  └──────────────────────────────────────────┘   │   │
│  │  ┌──────────────────────────────────────────┐   │   │
│  │  │  realsense2_camera (ROS2 package)        │   │   │
│  │  │  - Publie: /camera/odom/sample (200 Hz)  │   │   │
│  │  │  - Odométrie visuelle → PX4 EKF2         │   │   │
│  │  └──────────────────────────────────────────┘   │   │
│  │  ┌──────────────────────────────────────────┐   │   │
│  │  │  mqtt_bridge                             │   │   │
│  │  │  ← MÊME CODE QU'EN SIMULATION!           │   │   │
│  │  │  - Publie: MQTT drone/{id}/telemetry     │   │   │
│  │  └────────────────┬─────────────────────────┘   │   │
│  └───────────────────┼───────────────────────────┘   │
│                      │ WiFi/4G (latence 50-200ms)    │
│  ┌───────────────────▼─────────────────────────────┐  │
│  │  Intel RealSense T265 (Caméra Vision)         │  │
│  │  - Connexion: USB 3.0 → Raspberry Pi          │  │
│  │  - Tracking caméras stéréo fisheye            │  │
│  │  - IMU interne fusionné                       │  │
│  │  - Odométrie 200 Hz, précision ±1%            │  │
│  │  - Prix: ~200€                                │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  Batterie: 4S LiPo 14.8V 5000 mAh (~20 min vol)     │
│  Poids total: ~1.5 kg (drone + payload)             │
└─────────────────────────────────────────────────────┘
                      │ Internet (WiFi/4G)
                      ↓
┌─────────────────────────────────────────────────────────┐
│            SERVEUR CLOUD / LOCAL                        │
│                                                         │
│  MQTT Broker: AWS IoT Core / Mosquitto cloud            │
│  Backend: FastAPI (Docker Swarm / Kubernetes)           │
│  Frontend: React (CDN / Nginx)                          │
│  Database: PostgreSQL (production) / SQLite (dev)       │
└─────────────────────────────────────────────────────────┘

Latence PX4↔ROS2: <1 ms (UART direct)
Latence ROS2↔Backend: 50-200 ms (réseau)
CPU drone: ~50-60% (Raspberry Pi)
RAM drone: ~800 MB
```

---

## 3. Comparaison Détaillée par Composant

### 3.1. ROS2 - Le Middleware Central

| Aspect | Simulation | Production |
|--------|-----------|------------|
| **Plateforme** | Container Docker (Ubuntu 22.04) | Raspberry Pi 4 (Ubuntu 22.04 ARM64) |
| **Installation** | `docker compose build` | `apt install ros-humble-desktop` |
| **Packages** | MAVROS, custom bridges | **MAVROS + realsense2_camera** |
| **Code** | simulation/src/ | ✅ **Copie identique** sur `/home/pi/ros2_ws/src/` |
| **Lancement** | `docker compose up` | **systemd service** (autostart boot) |
| **RAM** | ~1 GB (partagé avec host) | ~500 MB (dédié) |

**Point Clé**: Le code ROS2 (MAVROS, mqtt_bridge) est **portable** entre sim et prod.

---

### 3.2. PX4 Autopilot

| Aspect | Simulation | Production |
|--------|-----------|------------|
| **Hardware** | Logiciel (process Linux) | **Pixhawk 6C (MCU STM32H7)** |
| **Firmware** | PX4 v1.16.0 SITL build | **PX4 v1.16.0 (même version!)** |
| **Runtime** | x86_64 executable | **ARM Cortex-M7 firmware** |
| **Capteurs** | Gazebo plugins (parfaits) | **Physiques** (IMU, Baro, Mag réels) |
| **MAVLink** | UDP localhost:14540 | **UART /dev/ttyUSB0:57600** |
| **Latence** | <1 ms | <1 ms (câble direct) |
| **Calibration** | ❌ Aucune (capteurs parfaits) | ✅ **Obligatoire** (Accel, Gyro, Mag, ESC) |
| **Safety Checks** | Relâchés (`COM_ARM_WO_GPS=1`) | **Stricts** (refuse ARM si échec) |

**Changement Code MAVROS** (1 ligne):
```python
# Simulation: simulation/src/mavros_launcher/launch/px4_sitl.launch.py:14
fcu_url = 'udp://:14540@127.0.0.1:14580'

# Production
fcu_url = '/dev/ttyUSB0:57600'
```

---

### 3.3. Vision / Odométrie

| Aspect | Simulation | Production |
|--------|-----------|------------|
| **Source** | Gazebo ground truth | **Intel RealSense T265** |
| **Topic ROS2** | `/model/x500_0/odometry` | `/camera/odom/sample` |
| **Node** | `vision_pose_bridge` (custom) | `realsense2_camera` (package officiel) |
| **Fréquence** | ~52 Hz | **200 Hz** |
| **Précision** | Parfaite (0 mm) | **±1% distance** (~10 cm sur 10 m) |
| **Bruit** | Aucun | **Réel** (lighting, fast motion) |
| **Coût** | Gratuit (logiciel) | **~200€** (hardware) |
| **Connexion** | IPC (Gazebo → ROS2) | **USB 3.0** (T265 → Raspberry Pi) |

**Changement Code** (adapter le topic):
```python
# Simulation: vision_pose_bridge.py
odometry_topic = '/model/x500_0/odometry'

# Production: Utilise directement /camera/odom/sample
# Publié par realsense2_camera, pas de bridge custom nécessaire
```

---

### 3.4. MQTT Communication

| Aspect | Simulation | Production |
|--------|-----------|------------|
| **Broker** | Container local `mqtt:1883` | **Cloud** `mqtt.evolutek-cloud.com:8883` |
| **Réseau** | Localhost (loopback) | **WiFi 2.4/5GHz ou 4G LTE** |
| **Latence** | <1 ms | **50-200 ms** (variable) |
| **Sécurité** | None (dev) | **TLS/SSL + username/password** |
| **Fiabilité** | 100% (local) | **Variable** (retry logic requis) |
| **QoS MQTT** | 0 (fire-and-forget) | **1** (at least once) |
| **Buffering** | Non nécessaire | **Oui** (si WiFi perdu) |

**Changements Code** (configuration):
```python
# Simulation: bridge_node.py:27-28
self.declare_parameter('mqtt_broker', 'mqtt')
self.declare_parameter('mqtt_port', 1883)

# Production (+ TLS)
self.declare_parameter('mqtt_broker', 'mqtt.evolutek-cloud.com')
self.declare_parameter('mqtt_port', 8883)
# + certificats TLS, retry logic, buffering offline
```

---

### 3.5. Multi-Drone

| Aspect | Simulation | Production |
|--------|-----------|------------|
| **Drones** | 3+ instances Gazebo | **3+ drones physiques** |
| **ROS2** | 1 container, 3 namespaces | **3 Raspberry Pi, 3 namespaces** |
| **PX4** | 3 SITL processes (ports 14540-42) | **3 Pixhawk (UART séparés)** |
| **MQTT** | 3 bridges → même broker local | **3 bridges → même broker cloud** |
| **Isolation** | Namespaces ROS2 (`/drone_1/`, `/drone_2/`) | ✅ **Identique** |
| **Scalabilité** | Limité CPU (5-6 drones @ 8-core) | **Limité budget** (1 drone = ~800€) |

**Architecture Identique**:
```
Simulation:
  Container ros2_integration
    ├─ MAVROS namespace=/drone_1/ → PX4 SITL port 14540
    ├─ MAVROS namespace=/drone_2/ → PX4 SITL port 14541
    └─ MAVROS namespace=/drone_3/ → PX4 SITL port 14542

Production:
  Drone 1 (Raspberry Pi #1)
    └─ MAVROS namespace=/drone_1/ → Pixhawk #1 UART
  Drone 2 (Raspberry Pi #2)
    └─ MAVROS namespace=/drone_2/ → Pixhawk #2 UART
  Drone 3 (Raspberry Pi #3)
    └─ MAVROS namespace=/drone_3/ → Pixhawk #3 UART
```

---

## 4. Flux de Données Comparé

### Commande ARM (Frontend → Drone)

**Simulation** (latence totale ~5-10 ms):
```
[1] Frontend → Backend HTTP POST /drones/drone_1/arm
    ↓ 1-2 ms (localhost)

[2] Backend → MQTT publish drone/drone_1/command {"command":"ARM"}
    ↓ <1 ms (container mqtt)

[3] mqtt_bridge (ROS2) → Service /mavros_node/arming
    ↓ <1 ms (local ROS2)

[4] MAVROS → MAVLink COMMAND_LONG(ARM_DISARM) UDP:14540
    ↓ <1 ms (localhost)

[5] PX4 SITL → Vérifie safety checks (relâchés) → ARM OK
    ↓ 1-2 ms

[6] Réponse propagée en sens inverse
    ↓ <5 ms total
```

**Production** (latence totale ~120-500 ms):
```
[1] Frontend → Backend HTTP POST /drones/drone_1/arm
    ↓ 10-50 ms (Internet)

[2] Backend → MQTT publish drone/drone_1/command {"command":"ARM"}
    ↓ 50-200 ms (WiFi/4G vers drone)

[3] mqtt_bridge (Raspberry Pi) → Service /mavros_node/arming
    ↓ <1 ms (local ROS2)

[4] MAVROS → MAVLink COMMAND_LONG(ARM_DISARM) UART:/dev/ttyUSB0
    ↓ ~2 ms (serial 57600 bauds)

[5] PX4 Pixhawk → Vérifie safety checks STRICTS
    ├─ ✅ Accel/Gyro/Mag calibrated
    ├─ ✅ Battery > 20%
    ├─ ✅ EKF2 converged
    ├─ ✅ Vision pose reçu < 1s
    └─ ✅ ARM OK (ou ❌ REFUSED)
    ↓ 10-50 ms (checks + ESC init)

[6] Réponse propagée en sens inverse
    ↓ 50-200 ms (réseau)

Total: 120-500 ms
```

---

## 5. Ce Qui Ne Change PAS

### 5.1. Code ROS2 (95% identique)

**Fichiers identiques**:
- ✅ `mqtt_bridge/mqtt_bridge/bridge_node.py` → Logique télémétrie/commandes
- ✅ `mavros_launcher/package.xml` → Dépendances ROS2
- ✅ Topics MAVROS → `/mavros/state`, `/mavros/local_position/pose`, etc.
- ✅ Services MAVROS → `/mavros_node/arming`, `/mavros_node/cmd/takeoff`

**Seuls changements**: Paramètres launch (URLs, ports)

### 5.2. Backend/Frontend (100% identique)

**Aucun changement** car backend communique via MQTT (abstraction):
- ✅ API endpoints: `POST /drones/{id}/arm`, `GET /drones/{id}/telemetry`
- ✅ WebSocket: `/ws/drone/{id}`
- ✅ MQTT topics: `drone/{id}/command`, `drone/{id}/telemetry`

### 5.3. PX4 Firmware (100% identique)

**Même version PX4 v1.16.0**:
- ✅ EKF2 algorithme identique (fusion IMU + Vision + Baro)
- ✅ MAVLink protocole identique
- ✅ Commander module identique (ARM/DISARM logic)

**Différence**: Paramètres plus stricts en production (safety checks)

---

## 6. Pourquoi ROS2 Reste en Production

### 6.1. MAVROS Gratuit

**Sans ROS2**, il faudrait:
```python
# Client MAVLink custom à écrire (~1 mois dev)
from pymavlink import mavutil

conn = mavutil.mavlink_connection('/dev/ttyUSB0:57600')
while True:
    msg = conn.recv_match(blocking=True)
    if msg.get_type() == 'LOCAL_POSITION_NED':
        # Parser manuellement 50+ types de messages
        x, y, z = msg.x, msg.y, msg.z
        # Publier MQTT (code redondant)
        mqtt_client.publish(...)
```

**Avec ROS2 + MAVROS**:
- ✅ MAVLink → ROS2 automatique (topics typés)
- ✅ Maintenance par communauté (bugs corrigés upstream)
- ✅ Compatible PX4 + ArduPilot

### 6.2. Support T265 Natif

**Intel RealSense T265** publie ROS2 nativement:
```bash
# Installation 1 ligne
sudo apt install ros-humble-realsense2-camera

# Lancement 1 commande
ros2 run realsense2_camera realsense2_camera_node
# → Publie /camera/odom/sample (nav_msgs/Odometry)
```

**Sans ROS2**: Utiliser `pyrealsense2` (API bas niveau, complexe)

### 6.3. Écosystème Robotique

**Packages ROS2 disponibles** (si besoins futurs):
- ✅ **SLAM**: `rtabmap_ros`, `cartographer_ros` → Cartographie 3D
- ✅ **Navigation**: `nav2` → Path planning, obstacle avoidance
- ✅ **Computer Vision**: `opencv_bridge`, `image_pipeline`
- ✅ **Swarm**: `px4_ros_com` → Communication inter-drone

**Sans ROS2**: Réinventer la roue pour chaque feature

---

## 7. Checklist Migration Sim → Prod

### 7.1. Hardware Requis (1 drone)

| Composant | Prix | Lien |
|-----------|------|------|
| **Pixhawk 6C** | ~200€ | Holybro |
| **Raspberry Pi 4 (4GB)** | ~60€ | Element14 |
| **Intel RealSense T265** | ~200€ | Intel (discontinued, stock limité) |
| **Telemetry Radio SiK** | ~50€ | HolyBro |
| **Frame + Moteurs + ESC** | ~150€ | Kit X500 compatible |
| **Batterie 4S LiPo 5000mAh** | ~40€ | Tattu |
| **Câbles/Connecteurs** | ~30€ | Divers |
| **microSD 64GB** | ~20€ | SanDisk |
| **Total** | **~750€** | Par drone |

### 7.2. Software Installation

```bash
# 1. Flash Raspberry Pi avec Ubuntu 22.04 Server ARM64
# Download: https://ubuntu.com/download/raspberry-pi

# 2. Install ROS2 Humble
sudo apt update && sudo apt upgrade
sudo apt install ros-humble-desktop

# 3. Install MAVROS
sudo apt install ros-humble-mavros ros-humble-mavros-extras
wget https://raw.githubusercontent.com/mavlink/mavros/master/mavros/scripts/install_geographiclib_datasets.sh
sudo bash ./install_geographiclib_datasets.sh

# 4. Install RealSense
sudo apt install ros-humble-realsense2-camera

# 5. Install MQTT
pip3 install paho-mqtt

# 6. Copy workspace depuis dev machine
scp -r simulation/src/* pi@drone_pi:/home/pi/ros2_ws/src/

# 7. Build workspace
cd ~/ros2_ws
colcon build --symlink-install

# 8. Configure permissions UART
sudo usermod -a -G dialout pi
# Reboot requis

# 9. Test connection Pixhawk
ros2 launch mavros_launcher px4_sitl.launch.py fcu_url:=/dev/ttyUSB0:57600

# 10. Configure autostart
sudo systemctl enable drone_ros2.service
```

### 7.3. Modifications Code (minimal)

**Fichier 1**: `px4_sitl.launch.py`
```diff
- default_value='udp://:14540@127.0.0.1:14580'
+ default_value='/dev/ttyUSB0:57600'
```

**Fichier 2**: `bridge_node.py`
```diff
- self.declare_parameter('mqtt_broker', 'mqtt')
- self.declare_parameter('mqtt_port', 1883)
+ self.declare_parameter('mqtt_broker', 'mqtt.evolutek-cloud.com')
+ self.declare_parameter('mqtt_port', 8883)
```

**Fichier 3**: Nouveau launch prod
```python
# production.launch.py
Node(package='realsense2_camera', ...)  # Au lieu de vision_pose_bridge
```

**Total**: ~20 lignes modifiées

---

## 8. Tableau Récapitulatif Final

| Critère | Simulation | Production | Changement Code |
|---------|-----------|------------|-----------------|
| **ROS2 Platform** | Docker container | Raspberry Pi | ❌ Aucun (même OS) |
| **PX4** | SITL process | Pixhawk hardware | ✅ 1 ligne (fcu_url) |
| **Vision** | Gazebo plugin | T265 camera | ✅ Launch file |
| **MQTT** | Local broker | Cloud broker | ✅ Config params |
| **MAVROS** | UDP:14540 | UART:57600 | ✅ 1 ligne |
| **mqtt_bridge** | Même code | Même code | ❌ Aucun |
| **Backend** | Même code | Même code | ❌ Aucun |
| **Frontend** | Même code | Même code | ❌ Aucun |
| **Calibration** | Aucune | Obligatoire | ⚠️ Procédure QGC |
| **Safety Checks** | Relâchés | Stricts | ⚠️ Params PX4 |

**Portabilité**: ✅ **95% du code identique** entre simulation et production

---

## 9. FAQ

### Q1: Pourquoi garder ROS2 en production ?

**R**: ROS2 fournit:
1. MAVROS (bridge MAVLink gratuit, testé)
2. Support T265/ZED (packages officiels)
3. Multi-drone (namespaces)
4. Écosystème robotique (SLAM, navigation)

Alternative sans ROS2 = ~1 mois dev + maintenance accrue.

### Q2: ROS2 consomme combien de RAM sur Raspberry Pi ?

**R**: ~500 MB (MAVROS + realsense2_camera + mqtt_bridge). Acceptable sur Pi 4 4GB.

### Q3: Et si WiFi est perdu en vol ?

**R**:
1. MQTT buffer messages (max 1000)
2. Drone continue mission autonome
3. Telemetry radio backup (SiK 915 MHz, portée 1km)
4. Reconnexion auto quand WiFi retrouvé

### Q4: Pourquoi pas MAVSDK au lieu de ROS2 ?

**R**: MAVSDK bon pour mono-drone simple, mais:
- Pas de support T265 natif
- Écosystème limité (pas de SLAM/nav)
- Latence gRPC supplémentaire

### Q5: Le code fonctionne vraiment sans changement ?

**R**: Oui à 95% ! Seuls changements:
- URLs (UDP → UART, localhost → cloud)
- Calibration (obligatoire en prod)
- Safety checks (stricts en prod)

---

## Références

- **Architecture détaillée**: `docs/ARCHITECTURE_DETAILED.md`
- **GPS-free operation**: `docs/GPS_FREE_OPERATION.md`
- **MAVROS docs**: https://github.com/mavlink/mavros
- **RealSense ROS2**: https://github.com/IntelRealSense/realsense-ros
- **PX4 User Guide**: https://docs.px4.io/

---

**Dernière mise à jour**: 2025-11-16
**Contact**: evolutek.ionis@gmail.com
