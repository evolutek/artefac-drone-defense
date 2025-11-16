# Architecture Détaillée - Artefac Drone Defense

**Objectif** : Documentation technique complète du flux de données et des composants du système de simulation multi-drone.

**Date** : 2025-11-13
**Version** : 1.0
**Audience** : Développeurs Evolutek

---

## Table des Matières

1. [Vue d'Ensemble](#vue-densemble)
2. [Composants Gazebo Harmonic](#composants-gazebo-harmonic)
3. [PX4 Autopilot et EKF2](#px4-autopilot-et-ekf2)
4. [ROS2 Integration Container](#ros2-integration-container)
   - 4.1 [MAVROS](#41-mavros)
   - 4.2 [Vision Pose Bridge](#42-vision-pose-bridge)
   - 4.3 [MQTT Bridge](#43-mqtt-bridge)
5. [Flux de Données Complet](#flux-de-données-complet)
6. [Comparaison Simulation vs Réalité](#comparaison-simulation-vs-réalité)
7. [Architecture Multi-Drone](#architecture-multi-drone)
8. [Précision et Ground Truth](#précision-et-ground-truth)

---

## 1. Vue d'Ensemble

### Architecture Système

```
┌─────────────────────────────────────────────────────────────────┐
│                        HOST MACHINE                             │
│                                                                 │
│  ┌───────────────────┐  ┌──────────────────┐  ┌─────────────┐   │
│  │   simulation      │  │ ros2_integration │  │   backend   │   │
│  │   container       │  │   container      │  │  container  │   │
│  │                   │  │                  │  │             │   │
│  │ ┌──────────────┐  │  │ ┌─────────────┐  │  │ ┌─────────┐ │   │
│  │ │   Gazebo     │  │  │ │   MAVROS    │  │  │ │ FastAPI │ │   │
│  │ │   Harmonic   │  │  │ │   Nodes     │  │  │ │   API   │ │   │
│  │ └──────────────┘  │  │ └─────────────┘  │  │ └─────────┘ │   │
│  │        ↕          │  │        ↕         │  │      ↕      │   │
│  │ ┌──────────────┐  │  │ ┌─────────────┐  │  │ ┌─────────┐ │   │
│  │ │  PX4 SITL    │  │  │ │ vision_pose │  │  │ │  MQTT   │ │   │
│  │ │   x 3        │  │  │ │  _bridge x3 │  │  │ │ Client  │ │   │
│  │ └──────────────┘  │  │ └─────────────┘  │  │ └─────────┘ │   │
│  │                   │  │        ↕         │  │             │   │
│  └─────────┬─────────┘  │ ┌─────────────┐  │  └─────────────┘   │
│            │            │ │ mqtt_bridge │  │         ↕          │
│            │            │ │    x 3      │  │         │          │
│            │            │ └─────────────┘  │         │          │
│            │            └────────┬─────────┘         │          │
│            │                     │                   │          │
│   MAVLink UDP (14540-14542)      │                   │          │
│            └─────────────────────┘                   │          │
│                                                      │          │
│                  ┌───────────────────────────────────┘          │
│                  │                                              │
│            ┌─────┴──────┐                                       │
│            │    MQTT    │                                       │
│            │   Broker   │                                       │
│            └────────────┘                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Paradigme de Communication

| Protocole | Usage | Caractéristiques |
|-----------|-------|------------------|
| **Gazebo Transport** | Gazebo ↔ PX4, Gazebo ↔ ROS2 | Protobuf, IPC/TCP, haute fréquence |
| **MAVLink** | PX4 ↔ MAVROS | UDP, point-à-point, temps-réel |
| **ROS2 DDS** | Nodes ROS2 entre eux | Multicast, découverte automatique |
| **MQTT** | ROS2 ↔ Backend | Pub/Sub, TCP, persistance possible |
| **HTTP/WebSocket** | Backend ↔ Frontend | REST + temps-réel |

---

## 2. Composants Gazebo Harmonic

### 2.1. Simulateur Physique

**Gazebo Harmonic** est le moteur de simulation physique qui calcule :
- **Dynamique des corps rigides** : Forces, moments, collisions
- **Environnement** : Gravité (9.81 m/s²), vent, température
- **Rendu visuel** : Caméras, ray-tracing (si GPU disponible)

**Fréquence** :
- Physique : 1000 Hz (timestep = 1 ms)
- Rendu : 30-60 FPS (si GUI activé)

### 2.2. Modèles de Drones

Chaque drone est un **modèle SDF** (Simulation Description Format) :

```xml
<!-- Exemple : models/x500_0/model.sdf -->
<model name="x500_0">
  <!-- Corps principal -->
  <link name="base_link">
    <inertial>
      <mass>1.5</mass>  <!-- kg -->
      <inertia>...</inertia>
    </inertial>
    <collision>...</collision>
    <visual>...</visual>
  </link>

  <!-- 4 moteurs (quadcopter) -->
  <link name="rotor_0">...</link>
  <link name="rotor_1">...</link>
  <link name="rotor_2">...</link>
  <link name="rotor_3">...</link>

  <!-- Capteurs embarqués -->
  <sensor name="imu_sensor" type="imu">
    <update_rate>400</update_rate>  <!-- Hz -->
  </sensor>

  <sensor name="air_pressure_sensor" type="air_pressure">
    <update_rate>50</update_rate>
  </sensor>

  <sensor name="magnetometer" type="magnetometer">
    <update_rate>100</update_rate>
  </sensor>
</model>
```

### 2.3. Plugins Gazebo → PX4

Gazebo utilise des **plugins** pour connecter les capteurs simulés à PX4 :

#### **A. Plugin IMU** (`libgazebo_imu_plugin.so`)

```cpp
// Publie sur Gazebo Transport :
topic: /imu
type: gz.msgs.IMU

// Données :
- linear_acceleration (x, y, z) [m/s²]
- angular_velocity (x, y, z) [rad/s]
- orientation (quaternion)
```

**PX4 souscrit** via Gazebo Transport et reçoit les données à 400 Hz.

#### **B. Plugin Barometer** (`libgazebo_barometer_plugin.so`)

```cpp
topic: /air_pressure
type: gz.msgs.FluidPressure

// Données :
- pressure [Pa]
- altitude [m] (calculée depuis pression)
```

#### **C. Plugin Magnetometer** (`libgazebo_magnetometer_plugin.so`)

```cpp
topic: /magnetometer
type: gz.msgs.Magnetometer

// Données :
- magnetic_field (x, y, z) [Gauss]
```

#### **D. Plugin Moteurs** (`libgazebo_motor_model.so`)

PX4 **commande** les moteurs via Gazebo Transport :

```cpp
// PX4 publie :
topic: /model/x500_0/command/motor_speed
type: gz.msgs.Actuators

// Données :
- velocity[0..3] [rad/s]  (vitesse de rotation des 4 moteurs)
```

Gazebo applique les forces/moments correspondants au modèle physique.

### 2.4. Ground Truth Odometry

Gazebo publie la **vérité terrain** (position/vitesse parfaites sans bruit) :

```cpp
// Topic 1 : Pose (position + orientation)
topic: /world/default/dynamic_pose/info
type: gz.msgs.Pose_V
rate: ~50 Hz

// Contenu pour chaque modèle :
message Pose_V {
  repeated Pose pose = 1;
}

message Pose {
  string name = 1;              // "x500_0", "x500_1", etc.
  Vector3d position = 2;        // (x, y, z) en mètres, frame ENU
  Quaternion orientation = 3;   // (w, x, y, z)
}

// Topic 2 : Odometry (pose + vitesses)
topic: /model/x500_0/odometry
type: gz.msgs.Odometry
rate: ~50 Hz

message Odometry {
  Pose pose = 1;
  Twist twist = 2;  // linear + angular velocity
}

message Twist {
  Vector3d linear = 1;   // (vx, vy, vz) en m/s
  Vector3d angular = 2;  // (wx, wy, wz) en rad/s
}
```

**Frame de référence** : ENU (East-North-Up)
- X : Est
- Y : Nord
- Z : Haut (altitude)

**Origine** : Centre du monde Gazebo (typiquement lat/lon configurés dans PX4_HOME_LAT/LON)

---

## 3. PX4 Autopilot et EKF2

### 3.1. PX4 SITL (Software In The Loop)

**PX4** est le firmware autopilot qui tourne en mode **SITL** (simulation) :

```bash
# Processus PX4 pour drone 0
/root/PX4-Autopilot/build/px4_sitl_default/bin/px4 \
  -i 0 \              # Instance ID
  -d /root/.ros/log   # Logs directory
```

**Modules PX4 actifs** :
- `sensors` : Acquisition capteurs (IMU, baro, mag)
- `ekf2` : Extended Kalman Filter (fusion capteurs)
- `commander` : Logique d'arming, modes de vol
- `navigator` : Missions, waypoints
- `mc_pos_control` : Contrôleur de position (multicopter)
- `mc_att_control` : Contrôleur d'attitude
- `mavlink` : Communication MAVLink

### 3.2. EKF2 Module

**EKF2** est l'estimateur d'état principal de PX4. C'est un **filtre de Kalman étendu** qui estime :

#### **États Estimés (24 dimensions)**

| État | Symbole | Unité | Description |
|------|---------|-------|-------------|
| Position | (x, y, z) | m | Position dans frame NED |
| Vitesse | (vx, vy, vz) | m/s | Vitesse linéaire |
| Quaternion | (q0, q1, q2, q3) | - | Orientation |
| Biais IMU accel | (bax, bay, baz) | m/s² | Offset accéléromètre |
| Biais IMU gyro | (bgx, bgy, bgz) | rad/s | Offset gyroscope |
| Vitesse vent | (wx, wy) | m/s | Vent horizontal estimé |
| Biais magnétique | (mbx, mby, mbz) | Gauss | Offset magnétomètre |

#### **Entrées (Mesures)**

**1. IMU (Obligatoire)** - Fréquence : 400 Hz
```cpp
// Accéléromètre
accel_x, accel_y, accel_z [m/s²]

// Gyroscope
gyro_x, gyro_y, gyro_z [rad/s]

// Utilisation : Prédiction de l'état à chaque timestep
```

**2. Vision/Odométrie (Configuration actuelle)** - Fréquence : ~52 Hz
```cpp
// Message MAVLink ODOMETRY
position: (x, y, z) [m]
velocity: (vx, vy, vz) [m/s]
orientation: (q0, q1, q2, q3)

// Utilisation : Correction de position/vitesse/yaw
// Empêche la dérive de l'intégration IMU
```

**3. Baromètre (Actif)** - Fréquence : 50 Hz
```cpp
pressure [Pa]
→ altitude = f(pressure)  // Formule barométrique

// Utilisation : Correction de l'altitude (Z)
// Plus fiable que vision pour altitude
```

**4. Magnétomètre (Optionnel)** - Fréquence : 100 Hz
```cpp
mag_x, mag_y, mag_z [Gauss]

// Utilisation : Correction du cap (yaw)
// Désactivable en indoor (interférences)
```

**5. GPS (Désactivé dans votre config)**
```cpp
// EKF2_GPS_CTRL = 0 → GPS ignoré
```

#### **Algorithme Simplifié**

```python
# Pseudo-code EKF2

class EKF2:
    def __init__(self):
        self.state = [0] * 24  # États (position, vitesse, orientation, biais)
        self.covariance = np.eye(24)  # Incertitude

    def predict(self, imu_accel, imu_gyro, dt):
        """
        Prédiction : Intègre les données IMU pour estimer nouvel état
        Problème : L'intégration dérive rapidement (quelques secondes)
        """
        # Intégration gyroscope → nouvelle orientation
        self.state[orientation] += imu_gyro * dt

        # Intégration accéléromètre → nouvelle vitesse/position
        # (en tenant compte de la gravité et l'orientation)
        accel_world = rotate(imu_accel, self.state[orientation]) - GRAVITY
        self.state[velocity] += accel_world * dt
        self.state[position] += self.state[velocity] * dt

        # Augmente l'incertitude (covariance)
        self.covariance += PROCESS_NOISE

    def update_vision(self, vision_position, vision_velocity):
        """
        Correction : Fusionne mesure vision avec prédiction IMU
        Résout la dérive de l'IMU
        """
        # Calcul innovation (différence mesure vs prédiction)
        innovation_pos = vision_position - self.state[position]
        innovation_vel = vision_velocity - self.state[velocity]

        # Calcul gain de Kalman (pondération optimale)
        K = self.covariance @ H.T @ inv(H @ self.covariance @ H.T + VISION_NOISE)

        # Correction état
        self.state[position] += K_pos @ innovation_pos
        self.state[velocity] += K_vel @ innovation_vel

        # Réduit l'incertitude
        self.covariance = (I - K @ H) @ self.covariance

    def update_barometer(self, baro_altitude):
        """
        Correction altitude uniquement
        """
        innovation_z = baro_altitude - self.state[position_z]
        # ... (similaire à update_vision)

    def get_estimate(self):
        """
        Retourne état estimé optimal
        """
        return {
            'position': self.state[0:3],
            'velocity': self.state[3:6],
            'orientation': self.state[6:10]
        }
```

#### **Configuration GPS-Free Actuelle**

Paramètres injectés au démarrage PX4 :

```bash
# simulation/start_px4_sitl.sh

# === Désactivation GPS ===
param set EKF2_GPS_CTRL 0        # GPS non utilisé par EKF2

# === Activation Vision ===
param set EKF2_EV_CTRL 15        # 0b1111 = position + velocity + yaw
param set EKF2_HGT_REF 0         # Barometer pour altitude (actuellement)
                                  # Note: Doc indique 3 (vision) mais code utilise 0

param set EKF2_EV_DELAY 0        # Pas de délai vision (simulation parfaite)
param set EKF2_EVP_NOISE 0.1     # Bruit position vision : 10 cm
param set EKF2_EVV_NOISE 0.1     # Bruit vitesse vision : 10 cm/s
param set EKF2_EVA_NOISE 0.05    # Bruit angle vision : ~3 degrés

# === Arming sans GPS ===
param set COM_ARM_WO_GPS 1       # Autoriser arming sans GPS fix
param set COM_PREARM_MODE 0      # Désactiver checks pre-arm stricts
param set COM_POS_FS_EPH 10.0    # Seuil erreur position (10m)
param set COM_VEL_FS_EVH 2.0     # Seuil erreur vitesse (2m/s)
```

**Conséquence** :
- EKF2 fusionne **IMU (400 Hz) + Vision (52 Hz) + Barometer (50 Hz)**
- Pas de GPS requis pour arming
- Précision attendue : ~10 cm (limitée par bruit vision configuré)

### 3.3. MAVLink Interface

PX4 communique via **MAVLink** (Micro Air Vehicle Link), un protocole binaire optimisé.

**Configuration Multi-Drone** :

```bash
# Drone 0
MAVLink UDP : 14540 (PX4 écoute) ↔ 14541 (MAVROS parle)
System ID   : 1

# Drone 1
MAVLink UDP : 14541 (PX4) ↔ 14542 (MAVROS)
System ID   : 2

# Drone 2
MAVLink UDP : 14542 (PX4) ↔ 14543 (MAVROS)
System ID   : 3
```

**Messages MAVLink clés** :

| Message | Direction | Fréquence | Contenu |
|---------|-----------|-----------|---------|
| `ATTITUDE` | PX4 → MAVROS | 50 Hz | Roll, pitch, yaw, rates |
| `LOCAL_POSITION_NED` | PX4 → MAVROS | 50 Hz | Position EKF2 (x, y, z) |
| `GLOBAL_POSITION_INT` | PX4 → MAVROS | 10 Hz | Position GPS (inactif ici) |
| `HEARTBEAT` | Bidirectionnel | 1 Hz | État connexion |
| `ODOMETRY` | MAVROS → PX4 | 52 Hz | Vision pose (input EKF2) |
| `COMMAND_LONG` | MAVROS → PX4 | On-demand | ARM, DISARM, TAKEOFF, etc. |

---

## 4. ROS2 Integration Container

Le container **ros2_integration** héberge 3 types de nodes ROS2 qui agissent comme **middleware** entre PX4 et le backend.

### 4.1. MAVROS

**MAVROS** (MAV ROS) est le pont officiel **ROS2 ↔ MAVLink**.

#### **Architecture MAVROS**

```
┌─────────────────────────────────────────────┐
│           MAVROS Node Process               │
│                                             │
│  ┌────────────────────────────────────────┐ │
│  │      MAVLink Interface                 │ │
│  │  - UDP socket (14540)                  │ │
│  │  - Serialize/Deserialize MAVLink msgs │ │
│  └───────────────┬────────────────────────┘ │
│                  ↕                           │
│  ┌───────────────────────────────────────┐  │
│  │      ROS2 Interface                   │  │
│  │  - Publishers (state, position, etc.) │  │
│  │  - Subscribers (vision input)         │  │
│  │  - Services (arming, takeoff)         │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

#### **Topics Publiés par MAVROS** (PX4 → ROS2)

| Topic | Message Type | Source MAVLink | Fréquence | Description |
|-------|-------------|----------------|-----------|-------------|
| `/mavros/state` | `mavros_msgs/State` | `HEARTBEAT` | 1 Hz | Connexion, armed, mode |
| `/mavros/local_position/pose` | `geometry_msgs/PoseStamped` | `LOCAL_POSITION_NED` | 50 Hz | **Output EKF2** : Position fusionnée |
| `/mavros/local_position/velocity_local` | `geometry_msgs/TwistStamped` | `LOCAL_POSITION_NED` | 50 Hz | Vitesse fusionnée |
| `/mavros/imu/data` | `sensor_msgs/Imu` | `ATTITUDE` + `HIGHRES_IMU` | 50 Hz | IMU filtré par PX4 |
| `/mavros/battery` | `sensor_msgs/BatteryState` | `BATTERY_STATUS` | 1 Hz | Voltage, %, temps restant |
| `/mavros/global_position/global` | `sensor_msgs/NavSatFix` | `GLOBAL_POSITION_INT` | 10 Hz | GPS (inactif) |

#### **Topics Souscrits par MAVROS** (ROS2 → PX4)

| Topic | Message Type | Destination MAVLink | Description |
|-------|-------------|---------------------|-------------|
| `/mavros/odometry/out` | `nav_msgs/Odometry` | `ODOMETRY` (ID 331) | **Input EKF2** : Vision pose |
| `/mavros/setpoint_position/local` | `geometry_msgs/PoseStamped` | `SET_POSITION_TARGET_LOCAL_NED` | Commande position |
| `/mavros/setpoint_velocity/cmd_vel_unstamped` | `geometry_msgs/Twist` | `SET_POSITION_TARGET_LOCAL_NED` | Commande vitesse |

#### **Services MAVROS** (ROS2 → PX4)

| Service | Type | MAVLink Command | Description |
|---------|------|-----------------|-------------|
| `/mavros/cmd/arming` | `CommandBool` | `COMPONENT_ARM_DISARM` | ARM/DISARM |
| `/mavros/cmd/takeoff` | `CommandTOL` | `NAV_TAKEOFF` | Décollage |
| `/mavros/cmd/land` | `CommandTOL` | `NAV_LAND` | Atterrissage |
| `/mavros/set_mode` | `SetMode` | `SET_MODE` | Changer mode de vol |

#### **Configuration QoS Critique**

MAVROS utilise des **Quality of Service** spécifiques pour certains topics :

```python
# /mavros/state nécessite TRANSIENT_LOCAL
qos_state = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,  # Reçoit dernier msg immédiatement
    history=HistoryPolicy.KEEP_LAST,
    depth=1
)

# /mavros/local_position/pose utilise QoS par défaut
qos_position = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10
)
```

**Pourquoi TRANSIENT_LOCAL ?**
- Quand un node ROS2 démarre et souscrit à `/mavros/state`, il reçoit **immédiatement** le dernier message publié (même si publié avant sa souscription)
- Critique pour l'état de connexion : évite d'attendre 1 seconde (fréquence heartbeat)

#### **Transformation de Frames**

MAVROS convertit automatiquement les frames de référence :

```
PX4 (MAVLink)           MAVROS (ROS2)
─────────────           ──────────────
NED (North-East-Down)   ENU (East-North-Up)

Conversion :
  x_enu =  y_ned
  y_enu =  x_ned
  z_enu = -z_ned
```

**Exemple** :
- PX4 dit : "position = (10, 5, -3) NED"
  → 10m Nord, 5m Est, 3m altitude
- MAVROS publie : "position = (5, 10, 3) ENU"
  → 5m Est, 10m Nord, 3m altitude

### 4.2. Vision Pose Bridge

**Rôle** : Convertir l'odométrie ground truth de Gazebo en format MAVROS/PX4.

**Fichier** : `simulation/src/mqtt_bridge/mqtt_bridge/vision_pose_bridge.py`

#### **Flux de Données**

```
Gazebo Harmonic
    ↓ gz.msgs.Pose_V @ /world/default/dynamic_pose/info (~50 Hz)
    ↓ gz.msgs.Odometry @ /model/x500_0/odometry (~50 Hz)

vision_pose_bridge Node (Python)
    ↓ Souscrit via gz.transport.Node() (API Python)
    ↓ Filtre par model_name : "x500_0", "x500_1", etc.
    ↓ Convertit ENU → ENU (même frame, mais format différent)
    ↓ Transforme velocities : world frame → body frame
    ↓ Ajoute covariances (matrices 6x6)
    ↓ Synchronise pose + velocity (buffering)

    ↓ nav_msgs/Odometry @ /mavros/odometry/out (~52 Hz)

MAVROS
    ↓ Convertit en MAVLink ODOMETRY message
    ↓ UDP → PX4 (port 14540)

PX4 EKF2
    ↓ Fusionne avec IMU + Barometer
```

#### **Code Clé : Transformation Vitesses**

**Problème** : Gazebo publie vitesses en **world frame** (ENU), mais PX4 attend vitesses en **body frame** (FRD : Forward-Right-Down).

```python
# vision_pose_bridge.py ligne ~150

def quaternion_to_rotation_matrix(q):
    """
    Convertit quaternion en matrice de rotation 3x3
    q = [w, x, y, z]
    """
    w, x, y, z = q
    R = np.array([
        [1 - 2*(y**2 + z**2),     2*(x*y - w*z),     2*(x*z + w*y)],
        [    2*(x*y + w*z), 1 - 2*(x**2 + z**2),     2*(y*z - w*x)],
        [    2*(x*z - w*y),     2*(y*z + w*x), 1 - 2*(x**2 + y**2)]
    ])
    return R

def transform_velocity_world_to_body(velocity_world, orientation_quat):
    """
    Transforme vitesse du world frame au body frame

    Exemple :
    - Drone orienté à 90° (yaw), se déplace vers le nord
    - World frame : velocity = (0, 1, 0) m/s (nord)
    - Body frame : velocity = (1, 0, 0) m/s (forward)
    """
    R_world_to_body = quaternion_to_rotation_matrix(orientation_quat).T
    velocity_body = R_world_to_body @ velocity_world
    return velocity_body

# Dans la callback
def on_gazebo_data(self, pose_msg, odom_msg):
    # Extraction données Gazebo
    position_world = [pose_msg.position.x, pose_msg.position.y, pose_msg.position.z]
    orientation = [pose_msg.orientation.w, pose_msg.orientation.x,
                   pose_msg.orientation.y, pose_msg.orientation.z]

    velocity_world = [odom_msg.twist.linear.x, odom_msg.twist.linear.y,
                      odom_msg.twist.linear.z]
    angular_vel_body = [odom_msg.twist.angular.x, odom_msg.twist.angular.y,
                        odom_msg.twist.angular.z]

    # Transformation critique
    velocity_body = transform_velocity_world_to_body(velocity_world, orientation)

    # Construction message ROS2
    odometry_msg = Odometry()
    odometry_msg.header.stamp = self.get_clock().now().to_msg()
    odometry_msg.header.frame_id = "map"  # World frame
    odometry_msg.child_frame_id = "base_link"  # Body frame

    # Position : reste en world frame
    odometry_msg.pose.pose.position.x = position_world[0]
    odometry_msg.pose.pose.position.y = position_world[1]
    odometry_msg.pose.pose.position.z = position_world[2]

    odometry_msg.pose.pose.orientation.w = orientation[0]
    odometry_msg.pose.pose.orientation.x = orientation[1]
    odometry_msg.pose.pose.orientation.y = orientation[2]
    odometry_msg.pose.pose.orientation.z = orientation[3]

    # Vitesse : maintenant en body frame !
    odometry_msg.twist.twist.linear.x = velocity_body[0]
    odometry_msg.twist.twist.linear.y = velocity_body[1]
    odometry_msg.twist.twist.linear.z = velocity_body[2]

    odometry_msg.twist.twist.angular.x = angular_vel_body[0]
    odometry_msg.twist.twist.angular.y = angular_vel_body[1]
    odometry_msg.twist.twist.angular.z = angular_vel_body[2]

    # Covariances (6x6 matrices pour pose et twist)
    # Diagonale : variances (écart-type²)
    # Hors-diagonale : corrélations (ici = 0)
    odometry_msg.pose.covariance = [
        0.01, 0, 0, 0, 0, 0,  # var(x) = 0.01 m²
        0, 0.01, 0, 0, 0, 0,  # var(y) = 0.01 m²
        0, 0, 0.01, 0, 0, 0,  # var(z) = 0.01 m²
        0, 0, 0, 0.01, 0, 0,  # var(roll) = 0.01 rad²
        0, 0, 0, 0, 0.01, 0,  # var(pitch) = 0.01 rad²
        0, 0, 0, 0, 0, 0.01   # var(yaw) = 0.01 rad²
    ]

    odometry_msg.twist.covariance = [
        0.01, 0, 0, 0, 0, 0,  # var(vx) = 0.01 (m/s)²
        0, 0.01, 0, 0, 0, 0,  # var(vy)
        0, 0, 0.01, 0, 0, 0,  # var(vz)
        0, 0, 0, 0.01, 0, 0,  # var(wx)
        0, 0, 0, 0, 0.01, 0,  # var(wy)
        0, 0, 0, 0, 0, 0.01   # var(wz)
    ]

    # Publication
    self.odom_pub.publish(odometry_msg)
```

#### **Pourquoi Body Frame pour Vitesses ?**

`★ Insight ─────────────────────────────────────`
**Frames de Référence : World vs Body**

Imaginez un drone qui se déplace vers le nord à 5 m/s :

**World Frame (ENU)** :
- X : 0 m/s (pas de mouvement vers l'est)
- Y : 5 m/s (mouvement vers le nord)
- Z : 0 m/s (pas de mouvement vertical)

**Body Frame (FRD)** :
- Si le drone **pointe vers le nord** : X = 5 m/s (forward)
- Si le drone **pointe vers l'est** : Y = 5 m/s (right)

Le **body frame suit l'orientation du drone**. C'est crucial pour le contrôle :
- Le contrôleur dit "avance à 5 m/s" → peu importe l'orientation absolue
- EKF2 préfère body frame pour les vitesses (cohérent avec IMU)
`─────────────────────────────────────────────────`

#### **Filtrage Multi-Drone**

```python
# vision_pose_bridge.py ligne ~60

def __init__(self):
    super().__init__('vision_pose_bridge')

    # Paramètre : quel modèle Gazebo surveiller ?
    self.declare_parameter('model_name', 'x500_0')
    self.model_name = self.get_parameter('model_name').value

    # Souscription Gazebo (topic partagé par tous les drones)
    self.gz_node.subscribe(
        gz.msgs.Pose_V,
        '/world/default/dynamic_pose/info',
        self.on_pose_callback
    )

def on_pose_callback(self, msg):
    """
    Reçoit ALL poses de TOUS les modèles dans le monde
    → Filtre uniquement celui qui nous intéresse
    """
    for pose in msg.pose:
        if pose.name == self.model_name:  # "x500_0", "x500_1", etc.
            self.current_pose = pose
            break
    # Ignore les autres drones
```

**Lancement Multi-Drone** :

```bash
# Drone 1
ros2 run mqtt_bridge vision_pose_bridge --ros-args \
    -p model_name:=x500_0 \
    -r /mavros/odometry/out:=/drone_1/mavros/odometry/out

# Drone 2
ros2 run mqtt_bridge vision_pose_bridge --ros-args \
    -p model_name:=x500_1 \
    -r /mavros/odometry/out:=/drone_2/mavros/odometry/out

# Drone 3
ros2 run mqtt_bridge vision_pose_bridge --ros-args \
    -p model_name:=x500_2 \
    -r /mavros/odometry/out:=/drone_3/mavros/odometry/out
```

**⚠️ Problème actuel** : Le remapping (`-r`) n'est pas implémenté → tous publient sur `/mavros/odometry/out` (conflit !).

### 4.3. MQTT Bridge

**Rôle** : Pont bidirectionnel **ROS2 ↔ MQTT** pour communication avec le backend.

**Fichier** : `simulation/src/mqtt_bridge/mqtt_bridge/bridge_node.py`

#### **Architecture**

```
┌─────────────────────────────────────────────┐
│         mqtt_bridge Node (Python)           │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │   ROS2 Interface                    │    │
│  │   - Subscribe: /mavros/state        │    │
│  │   - Subscribe: /mavros/local_pos... │    │
│  │   - Subscribe: /mavros/battery      │    │
│  │   - Publish: /mavros/cmd/...        │    │
│  └───────────────┬─────────────────────┘    │
│                  ↕                          │
│  ┌───────────────────────────────────────┐  │
│  │   MQTT Client (paho-mqtt)             │  │
│  │   - Publish: drone/{id}/telemetry     │  │
│  │   - Publish: drone/{id}/state         │  │
│  │   - Subscribe: drone/{id}/command     │  │
│  └───────────────┬───────────────────────┘  │
└──────────────────┼──────────────────────────┘
                   ↕
              MQTT Broker
```

#### **Flux ROS2 → MQTT (Telemetry)**

```python
# bridge_node.py ligne ~80

def __init__(self):
    super().__init__('mqtt_bridge')

    # Paramètre : ID du drone
    self.declare_parameter('drone_id', 'drone_1')
    self.drone_id = self.get_parameter('drone_id').value

    # Souscriptions ROS2
    self.state_sub = self.create_subscription(
        State,
        '/mavros/state',  # ← Devrait être /drone_1/mavros/state
        self.on_state_callback,
        10
    )

    self.pose_sub = self.create_subscription(
        PoseStamped,
        '/mavros/local_position/pose',
        self.on_pose_callback,
        10
    )

    self.battery_sub = self.create_subscription(
        BatteryState,
        '/mavros/battery',
        self.on_battery_callback,
        10
    )

    # Client MQTT
    self.mqtt_client = mqtt.Client()
    self.mqtt_client.connect("mqtt", 1883)  # Container name "mqtt"
    self.mqtt_client.loop_start()

def on_pose_callback(self, msg):
    """
    ROS2 pose → JSON → MQTT
    """
    telemetry = {
        'drone_id': self.drone_id,
        'timestamp': time.time(),
        'position': {
            'x': msg.pose.position.x,
            'y': msg.pose.position.y,
            'z': msg.pose.position.z
        },
        'orientation': {
            'w': msg.pose.orientation.w,
            'x': msg.pose.orientation.x,
            'y': msg.pose.orientation.y,
            'z': msg.pose.orientation.z
        }
    }

    # Publication MQTT
    topic = f"drone/{self.drone_id}/telemetry"
    payload = json.dumps(telemetry)
    self.mqtt_client.publish(topic, payload, qos=0)
```

#### **Flux MQTT → ROS2 (Commands)**

```python
# bridge_node.py ligne ~150

def __init__(self):
    # ... (suite __init__)

    # Souscription MQTT
    command_topic = f"drone/{self.drone_id}/command"
    self.mqtt_client.subscribe(command_topic)
    self.mqtt_client.on_message = self.on_mqtt_message

    # Clients ROS2 services
    self.arming_client = self.create_client(
        CommandBool,
        '/mavros/cmd/arming'
    )
    self.takeoff_client = self.create_client(
        CommandTOL,
        '/mavros/cmd/takeoff'
    )

def on_mqtt_message(self, client, userdata, msg):
    """
    Reçoit commande MQTT → appelle service ROS2
    """
    command = json.loads(msg.payload)

    if command['action'] == 'ARM':
        # Appel service MAVROS
        req = CommandBool.Request()
        req.value = True
        future = self.arming_client.call_async(req)
        future.add_done_callback(lambda f: self.send_command_result(f, 'ARM'))

    elif command['action'] == 'TAKEOFF':
        req = CommandTOL.Request()
        req.altitude = command.get('altitude', 2.5)
        future = self.takeoff_client.call_async(req)
        future.add_done_callback(lambda f: self.send_command_result(f, 'TAKEOFF'))

def send_command_result(self, future, action):
    """
    Envoie résultat commande sur MQTT
    """
    try:
        response = future.result()
        result = {
            'action': action,
            'success': response.success,
            'result': response.result
        }
    except Exception as e:
        result = {
            'action': action,
            'success': False,
            'error': str(e)
        }

    topic = f"drone/{self.drone_id}/command_result"
    self.mqtt_client.publish(topic, json.dumps(result))
```

#### **Topics MQTT**

| Topic | Direction | Format | Fréquence | Description |
|-------|-----------|--------|-----------|-------------|
| `drone/{id}/state` | ROS2 → MQTT | JSON | 1 Hz | Connexion, armed, mode |
| `drone/{id}/telemetry` | ROS2 → MQTT | JSON | 10 Hz | Position, orientation, batterie |
| `drone/{id}/command` | MQTT → ROS2 | JSON | On-demand | ARM, DISARM, TAKEOFF, LAND |
| `drone/{id}/command_result` | ROS2 → MQTT | JSON | On-demand | Succès/échec commande |

**Exemple Payload** :

```json
// drone/drone_1/telemetry
{
  "drone_id": "drone_1",
  "timestamp": 1699876543.123,
  "position": {"x": 1.23, "y": 4.56, "z": 2.50},
  "orientation": {"w": 0.99, "x": 0.01, "y": 0.02, "z": 0.03},
  "velocity": {"x": 0.5, "y": 0.0, "z": 0.0},
  "battery": {"voltage": 12.6, "percentage": 85, "remaining_time": 1200}
}

// drone/drone_1/command
{
  "action": "TAKEOFF",
  "altitude": 3.0
}

// drone/drone_1/command_result
{
  "action": "TAKEOFF",
  "success": true,
  "result": 0
}
```

---

## 5. Flux de Données Complet

### 5.1. Démarrage du Système

```
1. docker compose up
   ├─ Container simulation : Gazebo + PX4 x3
   ├─ Container ros2_integration : MAVROS x3 + bridges x6
   ├─ Container mqtt : Mosquitto broker
   └─ Container backend : FastAPI + MQTT client

2. Gazebo Harmonic démarre
   ├─ Charge monde : /root/PX4-Autopilot/Tools/simulation/gz/worlds/default.sdf
   ├─ Spawn modèles : x500_0, x500_1, x500_2
   └─ Active plugins : IMU, baro, mag, moteurs

3. PX4 SITL démarre (x3 instances)
   ├─ Instance 0 : port 14540, System ID 1
   ├─ Instance 1 : port 14541, System ID 2
   └─ Instance 2 : port 14542, System ID 3

   Chaque PX4 :
   ├─ Souscrit topics Gazebo (IMU, baro, mag) via gz.transport
   ├─ Lance module EKF2
   ├─ Ouvre socket MAVLink UDP
   └─ Attend connexion MAVROS

4. MAVROS démarre (x3 instances)
   ├─ MAVROS 1 : udp://localhost:14540, namespace /drone_1/
   ├─ MAVROS 2 : udp://localhost:14541, namespace /drone_2/
   └─ MAVROS 3 : udp://localhost:14542, namespace /drone_3/

   Chaque MAVROS :
   ├─ Connecte à PX4 via MAVLink
   ├─ Reçoit HEARTBEAT → publie /drone_N/mavros/state
   ├─ Reçoit LOCAL_POSITION_NED → publie /drone_N/mavros/local_position/pose
   └─ Attend données vision sur /drone_N/mavros/odometry/out

5. vision_pose_bridge démarre (x3 instances)
   ├─ Bridge 1 : model_name=x500_0 → /drone_1/mavros/odometry/out
   ├─ Bridge 2 : model_name=x500_1 → /drone_2/mavros/odometry/out
   └─ Bridge 3 : model_name=x500_2 → /drone_3/mavros/odometry/out

   Chaque bridge :
   ├─ Souscrit /world/default/dynamic_pose/info (Gazebo)
   ├─ Filtre pose par model_name
   ├─ Transforme velocities world → body
   └─ Publie nav_msgs/Odometry

6. mqtt_bridge démarre (x3 instances)
   ├─ Bridge 1 : drone_id=drone_1, namespace /drone_1/
   ├─ Bridge 2 : drone_id=drone_2, namespace /drone_2/
   └─ Bridge 3 : drone_id=drone_3, namespace /drone_3/

   Chaque bridge :
   ├─ Souscrit topics MAVROS (/drone_N/mavros/*)
   ├─ Publie MQTT (drone/drone_N/*)
   └─ Souscrit MQTT commands (drone/drone_N/command)

7. Backend démarre
   ├─ Connecte à MQTT broker
   ├─ Souscrit drone/+/telemetry (wildcard all drones)
   ├─ Lance serveur FastAPI (port 8000)
   └─ Lance WebSocket server
```

### 5.2. Cycle de Contrôle (50 Hz)

**Chaque 20 ms** (50 Hz), pour chaque drone :

```
┌─────────────────────────────────────────────────┐
│ Step 1 : Simulation Physique (Gazebo)          │
└─────────────────────────────────────────────────┘
Gazebo calcule :
  - Forces/moments sur drone (gravité, thrust moteurs, drag)
  - Nouvelle position/vitesse/orientation
  - Données capteurs (IMU, baro, mag) avec bruit simulé

Gazebo publie :
  ↓ /imu (400 Hz) → PX4
  ↓ /air_pressure (50 Hz) → PX4
  ↓ /world/default/dynamic_pose/info (50 Hz) → vision_pose_bridge

┌─────────────────────────────────────────────────┐
│ Step 2 : Vision Pose Bridge                    │
└─────────────────────────────────────────────────┘
vision_pose_bridge :
  1. Reçoit pose Gazebo (x, y, z, quat)
  2. Reçoit velocity Gazebo (vx, vy, vz) en world frame
  3. Transforme velocity en body frame (rotation matrix)
  4. Construit nav_msgs/Odometry avec covariances
  5. Publie /drone_N/mavros/odometry/out (52 Hz)

┌─────────────────────────────────────────────────┐
│ Step 3 : MAVROS → PX4                          │
└─────────────────────────────────────────────────┘
MAVROS :
  1. Reçoit nav_msgs/Odometry sur /drone_N/mavros/odometry/out
  2. Convertit en MAVLink ODOMETRY message
  3. Sérialise en binaire MAVLink
  4. Envoie UDP à PX4 (port 14540+N)

PX4 :
  1. Reçoit MAVLink ODOMETRY
  2. Désérialise
  3. Passe au module vehicle_odometry
  4. Disponible pour EKF2

┌─────────────────────────────────────────────────┐
│ Step 4 : EKF2 Estimation (PX4)                 │
└─────────────────────────────────────────────────┘
EKF2 (400 Hz pour IMU, 50 Hz pour corrections) :

  ** Prédiction (400 Hz) **
  1. Lit IMU : accel (ax, ay, az), gyro (gx, gy, gz)
  2. Intègre gyro → nouvelle orientation
  3. Transforme accel en world frame
  4. Intègre accel → nouvelle vitesse → nouvelle position
  5. Augmente covariance (incertitude)

  ** Correction Vision (52 Hz) **
  6. Lit odometry : position_meas, velocity_meas
  7. Innovation = mesure - prédiction
  8. Calcul gain de Kalman K
  9. Correction état : x_new = x_pred + K * innovation
  10. Réduit covariance

  ** Correction Barometer (50 Hz) **
  11. Lit baro : altitude_meas
  12. Correction uniquement Z

  ** Output **
  13. Publie local_position (position, velocity, yaw) → uORB
  14. Module mavlink lit uORB → envoie LOCAL_POSITION_NED

┌─────────────────────────────────────────────────┐
│ Step 5 : PX4 → MAVROS                          │
└─────────────────────────────────────────────────┘
PX4 :
  1. Module mavlink construit LOCAL_POSITION_NED message
  2. Sérialise MAVLink
  3. Envoie UDP à MAVROS (port 14541+N)

MAVROS :
  1. Reçoit LOCAL_POSITION_NED
  2. Extrait position (x, y, z), velocity (vx, vy, vz)
  3. Convertit NED → ENU
  4. Construit geometry_msgs/PoseStamped
  5. Publie /drone_N/mavros/local_position/pose

┌─────────────────────────────────────────────────┐
│ Step 6 : MQTT Bridge → Backend                 │
└─────────────────────────────────────────────────┘
mqtt_bridge :
  1. Callback ROS2 sur /drone_N/mavros/local_position/pose
  2. Extrait données (x, y, z, quat)
  3. Construit JSON telemetry
  4. Publie MQTT : drone/drone_N/telemetry

Backend :
  1. Callback MQTT sur drone/drone_N/telemetry
  2. Parse JSON
  3. Update base de données (SQLite)
  4. Broadcast WebSocket à frontend

┌─────────────────────────────────────────────────┐
│ Step 7 : Contrôle Moteurs (PX4)                │
└─────────────────────────────────────────────────┘
PX4 Position Controller :
  1. Lit setpoint (position désirée, ex: hover @ 2.5m)
  2. Lit état actuel (position EKF2)
  3. Calcul erreur : e = setpoint - state
  4. PID controller : thrust = Kp*e + Ki*integral(e) + Kd*derivative(e)
  5. Mixing : convertit thrust → vitesses moteurs individuelles
  6. Publie /model/x500_N/command/motor_speed → Gazebo

Gazebo :
  1. Reçoit motor_speed
  2. Calcule forces/moments (thrust = k * omega²)
  3. Applique au modèle physique

  → Cycle se répète
```

### 5.3. Commande Utilisateur (Exemple : TAKEOFF)

```
Frontend (React)
  User clique "Takeoff"
  ↓ HTTP POST /drones/drone_1/takeoff altitude=3.0

Backend (FastAPI)
  1. Reçoit requête
  2. Valide paramètres
  3. Publie MQTT : drone/drone_1/command
     {"action": "TAKEOFF", "altitude": 3.0}
  4. Attend résultat (timeout 10s)

mqtt_bridge (ROS2)
  1. Callback MQTT sur drone/drone_1/command
  2. Parse JSON
  3. Appelle service ROS2 : /drone_1/mavros/cmd/takeoff

MAVROS
  1. Reçoit service call
  2. Construit MAVLink COMMAND_LONG
     Command ID: MAV_CMD_NAV_TAKEOFF (22)
     Param7: altitude = 3.0
  3. Envoie UDP à PX4

PX4
  1. Reçoit MAV_CMD_NAV_TAKEOFF
  2. Module commander valide :
     - Drone armed ? ✓
     - Position valide ? ✓
     - Battery OK ? ✓
  3. Module navigator :
     - Active mode AUTO_TAKEOFF
     - Setpoint = position actuelle + (0, 0, 3.0)
  4. Position controller exécute
  5. Envoie ACK MAVLink : COMMAND_ACK (success=0)

MAVROS
  1. Reçoit COMMAND_ACK
  2. Répond au service call : success=True, result=0

mqtt_bridge
  1. Reçoit réponse service
  2. Publie MQTT : drone/drone_1/command_result
     {"action": "TAKEOFF", "success": true, "result": 0}

Backend
  1. Reçoit command_result
  2. Retourne HTTP 200 : {"status": "success", "altitude": 3.0}

Frontend
  1. Affiche "Takeoff successful"
  2. Watch telemetry : altitude augmente 0 → 3.0m (5-10s)
```

---

## 6. Comparaison Simulation vs Réalité

### 6.1. Tableau Comparatif

| Composant | Simulation (SITL) | Drone Réel | Différences |
|-----------|-------------------|------------|-------------|
| **Physique** | Gazebo Harmonic (calcul numérique) | Monde réel | Gazebo simplifie aérodynamique, pas de turbulences, pas d'effets sol |
| **PX4** | PX4 SITL (process Linux) | PX4 firmware (MCU Pixhawk) | Même code, mais SITL sans contraintes temps-réel strict |
| **IMU** | Gazebo plugin (parfait + bruit gaussien) | MPU6000 / ICM-20689 | Réel a drift, température-dépendant, vibrations |
| **GPS** | (Désactivé) | u-blox M8N / M9N | ±2m précision, 10 Hz, besoin ciel dégagé |
| **Vision** | Gazebo ground truth (parfait) | Intel RealSense T265 / ZED | Réel : limité portée (10m), lighting-dépendant, drift lent |
| **Barometer** | Gazebo (parfait + bruit) | MS5611 | Réel : dérive thermique, sensible météo |
| **Moteurs** | Gazebo physics (instantané) | ESC + brushless | Réel : délai 5-10ms, non-linéarités |
| **MAVLink** | UDP localhost (parfait) | Telemetry radio (SiK) | Réel : latence 20-50ms, packet loss, portée limitée |
| **MAVROS** | ROS2 node (Linux) | Companion computer (Raspberry Pi / Jetson) | Même code, mais réel a contraintes CPU/RAM |
| **Vision Pose Bridge** | Gazebo Transport API | ROS2 wrapper caméra | Réel utilise driver caméra (realsense2_camera node) |

### 6.2. Capteurs Réels Équivalents

#### **Remplacement Vision (Gazebo → Réel)**

**Option 1 : Intel RealSense T265**
```python
# ROS2 node : realsense2_camera
# Publie : /camera/odom/sample (nav_msgs/Odometry)

# Caractéristiques :
- Visual-Inertial Odometry (2 fisheye cameras + IMU)
- Fréquence : 200 Hz (IMU), 30 Hz (pose)
- Précision : ±1% distance parcourue (indoor)
- Portée : 10m (dépend texture/éclairage)
- Pas de calibration requise (factory calibrated)

# Remplacement dans architecture :
vision_pose_bridge → realsense2_camera node
  Publie directement /camera/odom/sample
  → Remap to /drone_N/mavros/odometry/out
```

**Option 2 : ZED 2 / ZED Mini**
```python
# ROS2 node : zed_wrapper
# Publie : /zed/odom (nav_msgs/Odometry)

# Caractéristiques :
- Stereo camera + depth + IMU
- Fréquence : 100 Hz (IMU), 30-60 Hz (pose)
- Précision : ±0.1m @ 10m
- SLAM intégré (loop closure)
- Plus lourd/cher que T265
```

**Option 3 : PX4Flow (optical flow)**
```python
# Capteur PX4 natif (pas de ROS2)
# Connexion directe à Pixhawk

# Caractéristiques :
- 1 caméra down-facing + sonar
- Mesure : vitesse 2D (vx, vy) + altitude
- Fonctionne jusqu'à 3m altitude
- Besoin texture au sol
- Pas de position absolue → drift lent
```

#### **Comparaison Précision**

| Source | Position Accuracy | Velocity Accuracy | Drift | Cost |
|--------|-------------------|-------------------|-------|------|
| Gazebo Ground Truth | Perfect (0 mm) | Perfect (0 mm/s) | None | - |
| Intel T265 | ±1% distance | ±0.1 m/s | ~1m / 100m | €200 |
| ZED 2 | ±0.1m @ 10m | ±0.05 m/s | With SLAM: minimal | €450 |
| PX4Flow | N/A (velocity only) | ±0.5 m/s | Position drift ~10m / 100m | €100 |
| GPS (comparaison) | ±2-5m | ±0.5 m/s | None (absolute) | €50 |

### 6.3. Architecture Réelle (Production)

```
Drone Physique
  ├─ Pixhawk 6C (MCU STM32H7)
  │   ├─ PX4 Firmware v1.16.0
  │   ├─ IMU : ICM-42688-P (400 Hz)
  │   ├─ Barometer : ICP-20100 (50 Hz)
  │   ├─ Magnetometer : BMM150 (100 Hz)
  │   └─ MAVLink UART → Companion computer
  │
  ├─ Raspberry Pi 4 / Jetson Nano (Companion)
  │   ├─ Ubuntu 22.04 + ROS2 Humble
  │   ├─ MAVROS (UART /dev/ttyUSB0)
  │   ├─ realsense2_camera node
  │   ├─ mqtt_bridge node
  │   └─ WiFi/4G → MQTT broker cloud
  │
  ├─ Intel RealSense T265 (USB → Raspberry Pi)
  │   └─ Publie /camera/odom/sample (200 Hz)
  │
  ├─ Telemetry Radio (SiK 915 MHz)
  │   └─ MAVLink → Ground Control Station (QGroundControl)
  │
  └─ Battery 4S LiPo (14.8V, 5000 mAh)

Backend (Cloud / Local Server)
  ├─ MQTT Broker (AWS IoT / Mosquitto)
  ├─ FastAPI (Docker)
  └─ Database (PostgreSQL / SQLite)

Frontend (Web / Mobile)
  └─ React / React Native
```

**Différences Architecture Réelle** :

1. **Pas de Gazebo** : Monde réel = simulateur physique gratuit 😄
2. **Pixhawk au lieu de PX4 SITL** : MCU dédié, contraintes temps-réel strictes
3. **UART au lieu d'UDP** : MAVLink via serial (57600 bauds), plus robuste que WiFi
4. **Caméra réelle** : T265 remplace vision_pose_bridge, même interface ROS2
5. **Telemetry radio** : Backup si WiFi/4G perdu, portée ~1km
6. **Companion computer** : Raspberry Pi embarqué, contraintes CPU/RAM/Power
7. **MQTT via réseau** : Latence 50-200ms (vs <1ms simulation), need retry logic

### 6.4. Calibration Requise (Réel)

En simulation : **Aucune calibration nécessaire** (capteurs parfaits)

Drone réel nécessite :

1. **Accel Calibration** (6-point calibration)
   ```bash
   # QGroundControl → Sensors → Accelerometer
   # Placer drone : level, nose up, nose down, left, right, upside down
   # Mesure gravity vector dans 6 orientations
   ```

2. **Gyro Calibration** (au sol, immobile)
   ```bash
   # Mesure biais gyro (offset au repos)
   # Critique : ne pas bouger drone pendant 30s !
   ```

3. **Mag Calibration** (rotation complète)
   ```bash
   # QGroundControl → Sensors → Compass
   # Rotation drone dans tous axes (dessin sphère)
   # Compense hard/soft iron distortions
   ```

4. **ESC Calibration** (range PWM moteurs)
   ```bash
   # Ensure moteurs répondent correctement 1000-2000 µs
   ```

5. **Vision-IMU Extrinsics** (T265)
   ```bash
   # Transformation spatiale : IMU frame → Camera frame
   # T265 : pre-calibrated en usine
   # ZED : calibration automatique au boot
   ```

---

## 7. Architecture Multi-Drone

### 7.0. Gestion Dynamique des Drones (Spawn/Despawn)

Le système supporte l'ajout et le retrait de drones **à chaud** sans redémarrer la simulation.

#### **Scripts de Gestion**

**spawn_drone.sh** : Ajouter un drone
```bash
# Syntaxe
bash spawn_drone.sh <drone_num> [x] [y] [z]

# Exemples
bash spawn_drone.sh 0          # Spawn drone_1 à position par défaut
bash spawn_drone.sh 1 5 5 0.5  # Spawn drone_2 à (5, 5, 0.5)
bash spawn_drone.sh 2 -3 0 1   # Spawn drone_3 à (-3, 0, 1)
```

**Processus de Spawn** (3 étapes, ~10-15 secondes) :

```
[1/3] Gazebo Model Spawn
  ↓ gz service /world/default/create
  ↓ SDF: <model name="x500_N"><pose>X Y Z 0 0 0</pose>...</model>
  ↓ Modèle x500_N apparaît dans Gazebo à position (X, Y, Z)

[2/3] PX4 SITL Launch
  ↓ PX4_GZ_MODEL_NAME=x500_N ./px4 -i N
  ↓ PX4 instance N démarre (port 14540+N)
  ↓ PX4 se connecte au modèle Gazebo x500_N
  ↓ Sensors actifs : IMU (400Hz), Baro (50Hz), Mag (100Hz)

[3/3] ROS2 Nodes Launch
  ↓ MAVROS : namespace=/drone_(N+1)/, fcu_url=udp://:14540+N@:14580+N
  ↓ vision_pose_bridge : model_name=x500_N, namespace=/drone_(N+1)/
  ↓ mqtt_bridge : drone_id=drone_(N+1), namespace=/drone_(N+1)/
  ↓ Attend MAVROS services (~5s)
  ↓ Enable vision pose: ros2 param set .../global_position.use_vision true

  → Drone opérationnel ✓
```

**despawn_drone.sh** : Retirer un drone
```bash
# Syntaxe
bash despawn_drone.sh <drone_num>

# Exemples
bash despawn_drone.sh 0  # Remove drone_1
bash despawn_drone.sh 2  # Remove drone_3
```

**Processus de Despawn** (3 étapes, ~3 secondes) :

```
[1/3] Stop ROS2 Nodes
  ↓ kill MAVROS + bridges (via PIDs /tmp/*.pid)
  ↓ Graceful shutdown (SIGINT) → Force (SIGKILL) si timeout
  ↓ Cleanup PID files

[2/3] Stop PX4 SITL
  ↓ kill px4 -i N (via PID /tmp/px4_N.pid)
  ↓ Graceful shutdown → Force kill

[3/3] Remove Gazebo Model
  ↓ gz service /world/default/remove
  ↓ Entity: name=x500_N, type=MODEL
  ↓ Modèle disparaît de Gazebo

  → Drone retiré ✓
```

#### **Utilisation depuis Docker**

```bash
# Spawn drone_1 à position par défaut
docker exec -it artefac_ros2_integration bash -c "
  source /opt/ros/humble/setup.bash &&
  source /root/ros2_ws/install/setup.bash &&
  bash /root/simulation/spawn_drone.sh 0
"

# Spawn drone_2 à position (5, 5, 0.5)
docker exec -it artefac_ros2_integration bash -c "
  source /opt/ros/humble/setup.bash &&
  source /root/ros2_ws/install/setup.bash &&
  bash /root/simulation/spawn_drone.sh 1 5 5 0.5
"

# Remove drone_1
docker exec -it artefac_ros2_integration bash -c "
  bash /root/simulation/despawn_drone.sh 0
"

# List active drones
docker exec -it artefac_ros2_integration bash -c "
  source /opt/ros/humble/setup.bash &&
  ros2 topic list | grep /drone_
"
```

#### **Limitations et Considérations**

**Limites Techniques** :

| Ressource | Consommation/Drone | Limite Recommandée |
|-----------|-------------------|-------------------|
| **CPU** | ~10-15% (8-core) | Max 5-6 drones temps-réel |
| **RAM** | ~500 MB | Max 10-15 drones (16 GB RAM) |
| **Network** | DDS multicast | ~20 drones (puis tuning requis) |

**Numérotation Drone** :
- `drone_num` : 0-indexed (0, 1, 2, ...)
- `drone_id` : 1-indexed (drone_1, drone_2, drone_3, ...)
- `model_name` : 0-indexed (x500_0, x500_1, x500_2, ...)
- `system_id` : 1-indexed MAVLink (1, 2, 3, ...)

**Position par Défaut** :
```python
# spawn_drone.sh ligne 26
X = drone_num * 3  # 0, 3, 6, 9, ...
Y = 0
Z = 0.5
# → Drones espacés de 3m en ligne sur l'axe X
```

**Ports MAVLink** :
```
Drone 0: FCU 14540 ↔ GCS 14580
Drone 1: FCU 14541 ↔ GCS 14581
Drone 2: FCU 14542 ↔ GCS 14582
...
Limite : 255 drones (MAVLink System ID max)
```

#### **Roadmap : Intégration Backend/Frontend**

**Phase 1 (Actuel)** ✅ :
- Scripts shell manuels
- Spawn/despawn via `docker exec`

**Phase 2 (Planifié)** :
```python
# Backend API
@app.post("/drones/spawn")
async def spawn_drone(position: Position):
    """
    Spawn nouveau drone dynamiquement
    Calls spawn_drone.sh via subprocess
    Returns: drone_id, estimated ready time
    """
    # Auto-assign drone_num (find next available)
    # Execute spawn_drone.sh
    # Poll ROS2 topics until drone ready
    # Register in DB
    return {"drone_id": "drone_4", "eta_seconds": 15}

@app.delete("/drones/{drone_id}")
async def despawn_drone(drone_id: str):
    """
    Remove drone from simulation
    Calls despawn_drone.sh
    """
    # Execute despawn_drone.sh
    # Cleanup DB
    return {"status": "removed"}
```

**Phase 3 (Future)** :
- Frontend UI : Add/Remove drone buttons
- Drag-and-drop drone placement in 3D view
- Auto grid placement (spacing optimization)
- Benchmarking tool (stress test jusqu'à X drones)

### 7.1. Namespaces ROS2

**Principe** : Isoler chaque drone dans son propre namespace pour éviter collisions.

```
Global namespace (/)
  ├─ drone_1/
  │   ├─ mavros/
  │   │   ├─ state
  │   │   ├─ local_position/pose
  │   │   ├─ odometry/out
  │   │   └─ cmd/arming (service)
  │   └─ diagnostics
  │
  ├─ drone_2/
  │   ├─ mavros/
  │   │   ├─ state
  │   │   ├─ local_position/pose
  │   │   ├─ odometry/out
  │   │   └─ cmd/arming (service)
  │   └─ diagnostics
  │
  └─ drone_3/
      └─ mavros/ (...)
```

**Avantages** :
- ✅ Pas de collision topics
- ✅ Facile à scale (ajouter drone_4, drone_5...)
- ✅ Compatible avec ROS2 tools (`ros2 topic echo /drone_1/mavros/state`)
- ✅ Permet communication inter-drone si nécessaire

### 7.2. Configuration Multi-Drone

#### **A. docker-compose.yml**

```yaml
services:
  simulation:
    image: px4-gazebo:latest
    environment:
      NUM_DRONES: 3  # Variable pour spawn N drones
    command: >
      bash -c "
      # Lance Gazebo
      gz sim -r -v4 /root/worlds/multi_drone.sdf &

      # Lance PX4 pour chaque drone
      for i in $(seq 0 2); do
        cd /root/PX4-Autopilot
        DRONE_ID=$i ./start_px4_sitl.sh &
      done

      wait
      "

  ros2_integration:
    image: ros2-mavros:latest
    depends_on:
      - simulation
    command: >
      bash -c "
      source /opt/ros/humble/setup.bash
      source /root/ws/install/setup.bash

      # Lance MAVROS pour chaque drone
      for i in {1..3}; do
        DRONE_NUM=$((i-1))
        ros2 launch mavros_launcher mavros.launch.py \
          namespace:=drone_$i \
          fcu_url:=udp://:$((14540+DRONE_NUM))@localhost:$((14541+DRONE_NUM)) \
          system_id:=$i &
      done

      # Lance vision_pose_bridge pour chaque drone
      for i in {1..3}; do
        DRONE_NUM=$((i-1))
        ros2 run mqtt_bridge vision_pose_bridge \
          --ros-args \
          -p model_name:=x500_$DRONE_NUM \
          -p namespace:=drone_$i &
      done

      # Lance mqtt_bridge pour chaque drone
      for i in {1..3}; do
        ros2 launch mqtt_bridge mqtt_bridge.launch.py \
          drone_id:=drone_$i \
          ros_namespace:=drone_$i &
      done

      wait
      "
```

#### **B. Launch File MAVROS (modifié)**

`simulation/src/mavros_launcher/launch/mavros.launch.py` :

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    namespace_arg = DeclareLaunchArgument(
        'namespace',
        default_value='drone_1',
        description='Namespace for this MAVROS instance'
    )

    fcu_url_arg = DeclareLaunchArgument(
        'fcu_url',
        default_value='udp://:14540@localhost:14541',
        description='FCU connection URL'
    )

    system_id_arg = DeclareLaunchArgument(
        'system_id',
        default_value='1',
        description='MAVLink System ID'
    )

    mavros_node = Node(
        package='mavros',
        executable='mavros_node',
        namespace=LaunchConfiguration('namespace'),  # ← Applique namespace
        parameters=[{
            'fcu_url': LaunchConfiguration('fcu_url'),
            'system_id': LaunchConfiguration('system_id'),
            'target_system_id': LaunchConfiguration('system_id'),
            'target_component_id': 1,
            'plugin_allowlist': [
                'sys_status',
                'sys_time',
                'imu',
                'local_position',
                'global_position',
                'command',
                'setpoint_position',
                'odometry'
            ]
        }],
        output='screen'
    )

    return LaunchDescription([
        namespace_arg,
        fcu_url_arg,
        system_id_arg,
        mavros_node
    ])
```

#### **C. Vision Pose Bridge (modifié)**

`simulation/src/mqtt_bridge/mqtt_bridge/vision_pose_bridge.py` :

```python
class VisionPoseBridge(Node):
    def __init__(self):
        super().__init__('vision_pose_bridge')

        # Paramètres
        self.declare_parameter('model_name', 'x500_0')
        self.declare_parameter('namespace', 'drone_1')  # ← NOUVEAU

        self.model_name = self.get_parameter('model_name').value
        self.namespace = self.get_parameter('namespace').value

        # Topic avec namespace
        odom_topic = f'/{self.namespace}/mavros/odometry/out'

        self.odom_pub = self.create_publisher(
            Odometry,
            odom_topic,  # ← Namespace dynamique
            qos_profile
        )

        # ... (reste identique)
```

#### **D. MQTT Bridge (modifié)**

`simulation/src/mqtt_bridge/mqtt_bridge/bridge_node.py` :

```python
class MQTTBridge(Node):
    def __init__(self):
        # IMPORTANT : Node dans namespace
        super().__init__('mqtt_bridge', namespace=self.get_namespace())

        self.declare_parameter('drone_id', 'drone_1')
        self.drone_id = self.get_parameter('drone_id').value

        # Souscriptions RELATIF au namespace
        # Si namespace=/drone_1, alors '/mavros/state' → '/drone_1/mavros/state'
        self.state_sub = self.create_subscription(
            State,
            'mavros/state',  # ← Relatif (pas de / au début)
            self.on_state_callback,
            10
        )

        self.pose_sub = self.create_subscription(
            PoseStamped,
            'mavros/local_position/pose',
            self.on_pose_callback,
            10
        )

        # Services RELATIF
        self.arming_client = self.create_client(
            CommandBool,
            'mavros/cmd/arming'
        )
```

### 7.3. Vérification Isolation

**Test Isolation** : Vérifier que bouger drone_1 n'affecte pas EKF2 de drone_2.

```python
# test_ekf2_multi_drone_isolation.py

import rclpy
from geometry_msgs.msg import PoseStamped
import time

def test_multi_drone_isolation():
    """
    Vérifie que chaque drone a son propre EKF2 indépendant
    """
    rclpy.init()
    node = rclpy.create_node('test_isolation')

    # Souscriptions
    drone1_pose = {'data': None}
    drone2_pose = {'data': None}

    def drone1_callback(msg):
        drone1_pose['data'] = msg

    def drone2_callback(msg):
        drone2_pose['data'] = msg

    sub1 = node.create_subscription(
        PoseStamped,
        '/drone_1/mavros/local_position/pose',
        drone1_callback,
        10
    )

    sub2 = node.create_subscription(
        PoseStamped,
        '/drone_2/mavros/local_position/pose',
        drone2_callback,
        10
    )

    # Attente données
    timeout = time.time() + 10
    while (drone1_pose['data'] is None or drone2_pose['data'] is None) and time.time() < timeout:
        rclpy.spin_once(node, timeout_sec=0.1)

    assert drone1_pose['data'] is not None, "Drone 1 position not received"
    assert drone2_pose['data'] is not None, "Drone 2 position not received"

    # Position initiale drone 2
    initial_pos2 = drone2_pose['data'].pose.position

    # Commande drone 1 : TAKEOFF
    # (via backend API : POST /drones/drone_1/takeoff)

    # Attendre 5 secondes (drone 1 monte)
    time.sleep(5)

    # Vérifier drone 2 n'a PAS bougé
    rclpy.spin_once(node, timeout_sec=0.1)
    current_pos2 = drone2_pose['data'].pose.position

    delta_x = abs(current_pos2.x - initial_pos2.x)
    delta_y = abs(current_pos2.y - initial_pos2.y)
    delta_z = abs(current_pos2.z - initial_pos2.z)

    # Tolérance : 1 cm (bruit numérique EKF2)
    assert delta_x < 0.01, f"Drone 2 X moved {delta_x}m (expected <0.01m)"
    assert delta_y < 0.01, f"Drone 2 Y moved {delta_y}m"
    assert delta_z < 0.01, f"Drone 2 Z moved {delta_z}m"

    print("✅ Multi-drone isolation: PASS")

    node.destroy_node()
    rclpy.shutdown()
```

---

## 8. Précision et Ground Truth

### 8.1. Qu'est-ce que le Ground Truth ?

**Ground Truth** = La "vérité absolue", la valeur réelle exacte.

En simulation :
- Gazebo connaît la position **exacte** de chaque objet (calcul déterministe)
- `/world/default/dynamic_pose/info` publie cette position parfaite
- **Aucun bruit, aucune erreur** (sauf si configuré explicitement)

En réalité :
- **Pas de ground truth** disponible !
- On ne connaît jamais la position exacte (tous les capteurs ont des erreurs)
- Pour tests : utiliser système de référence ultra-précis
  - Motion capture (Vicon, OptiTrack) : ±1mm @ 100Hz, coût €50k+
  - Total station (géomètre) : ±2mm, statique seulement
  - RTK-GPS : ±2cm, outdoor seulement

### 8.2. Erreur EKF2 vs Ground Truth

**En simulation** :

```python
# test_ekf2_accuracy.py

def test_ekf2_accuracy():
    """
    Compare position EKF2 vs ground truth Gazebo
    """
    # Position EKF2 (estimée)
    ekf2_pos = get_position('/drone_1/mavros/local_position/pose')
    # Position Gazebo (vérité)
    gt_pos = get_gazebo_ground_truth('x500_0')

    # Erreur
    error_x = abs(ekf2_pos.x - gt_pos.x)
    error_y = abs(ekf2_pos.y - gt_pos.y)
    error_z = abs(ekf2_pos.z - gt_pos.z)
    error_3d = math.sqrt(error_x**2 + error_y**2 + error_z**2)

    # Seuils
    assert error_3d < 0.50, f"Position error {error_3d:.3f}m > 0.50m"
    # ^^^ 50 cm = "réaliste" pour vision indoor

    # Si on veut tester précision simulation pure :
    # assert error_3d < 0.10, f"Position error {error_3d:.3f}m > 0.10m"
    # ^^^ 10 cm = très strict, simulation sans bruit
```

**Pourquoi 50 cm est "réaliste" ?**

Votre configuration EKF2 :
```bash
param set EKF2_EVP_NOISE 0.1  # Vision position noise = 10 cm std dev
```

**Théorie statistique** :
- Bruit gaussien σ = 0.1 m (écart-type)
- 68% des mesures dans ±σ (±10 cm)
- 95% des mesures dans ±2σ (±20 cm)
- 99.7% des mesures dans ±3σ (±30 cm)

EKF2 fusionne multiples mesures bruitées → erreur finale ≈ σ/√N
- Si 50 mesures vision dans fenêtre EKF2 : erreur ≈ 10/√50 ≈ 1.4 cm

**Mais** : Drift IMU entre corrections vision, délai vision (10-20ms), etc.
→ Erreur réelle simulation : **2-5 cm** typiquement
→ Erreur réelle hardware : **10-50 cm** (dépend qualité caméra, lighting, calibration)

### 8.3. Niveaux de Précision Recommandés

| Application | Précision Requise | Configuration EKF2 | Capteurs |
|-------------|-------------------|---------------------|----------|
| **Delivery (outdoor)** | < 2 m | GPS + Baro | GPS standard |
| **Warehouse navigation** | < 50 cm | Vision + IMU | T265 / ZED |
| **Inspection (proximity)** | < 10 cm | Stereo vision + IMU | ZED 2 + Lidar |
| **Research (simulation)** | < 5 cm | Ground truth + IMU | Gazebo perfect |
| **Precision landing** | < 5 cm | AprilTag vision | Downward camera |

**Pour vos tests** :

```python
# Tests à 3 niveaux de strictness

def test_ekf2_coarse_accuracy():
    """Niveau laxiste : équivalent GPS"""
    error = compute_error()
    assert error < 2.0, "Coarse accuracy failed"

def test_ekf2_realistic_accuracy():
    """Niveau réaliste : vision indoor"""
    error = compute_error()
    assert error < 0.5, "Realistic accuracy failed"

def test_ekf2_strict_accuracy():
    """Niveau strict : simulation pure"""
    error = compute_error()
    assert error < 0.1, "Strict accuracy failed"
```

**Recommandation** : Commencez avec **realistic (< 0.5m)**, puis abaissez seuil progressivement selon résultats.

---

## 9. Résumé Flux de Données

### 9.1. Diagramme Séquence Complet

```
Gazebo          PX4           MAVROS      vision_bridge   mqtt_bridge   Backend
  │              │              │              │               │            │
  ├─ IMU 400Hz ─→│              │              │               │            │
  ├─ Baro 50Hz ─→│              │              │               │            │
  │              │              │              │               │            │
  ├─ Pose 50Hz ──┼──────────────┼─────────────→│               │            │
  ├─ Odom 50Hz ──┼──────────────┼─────────────→│               │            │
  │              │              │              │               │            │
  │              │              │              │               │            │
  │              │              │         Transform            │            │
  │              │              │         world→body           │            │
  │              │              │              │               │            │
  │              │              │        Odom 52Hz             │            │
  │              │              │←─────────────┤               │            │
  │              │              │              │               │            │
  │              │        ODOMETRY MAVLink     │               │            │
  │              │←─────────────┤              │               │            │
  │              │              │              │               │            │
  │            EKF2             │              │               │            │
  │         Fusion IMU          │              │               │            │
  │         +Vision+Baro        │              │               │            │
  │              │              │              │               │            │
  │              │   LOCAL_POSITION_NED        │               │            │
  │              ├─────────────→│              │               │            │
  │              │              │              │               │            │
  │              │        /mavros/local_position/pose          │            │
  │              │              ├──────────────┼──────────────→│            │
  │              │              │              │               │            │
  │              │              │              │        MQTT telemetry      │
  │              │              │              │               ├───────────→│
  │              │              │              │               │            │
  │              │              │              │               │      WebSocket
  │              │              │              │               │            ├→ Frontend
  │              │              │              │               │            │
  │     User: "TAKEOFF"         │              │               │            │
  │              │              │              │               │      HTTP POST
  │              │              │              │               │←───────────┤
  │              │              │              │               │            │
  │              │              │              │        MQTT command        │
  │              │              │              │←──────────────┤            │
  │              │              │              │               │            │
  │              │              │    Service /cmd/takeoff      │            │
  │              │              │←─────────────┼───────────────┤            │
  │              │              │              │               │            │
  │              │   COMMAND_LONG MAVLink      │               │            │
  │              │←─────────────┤              │               │            │
  │              │              │              │               │            │
  │         Commander           │              │               │            │
  │         validates           │              │               │            │
  │              │              │              │               │            │
  │         Navigator           │              │               │            │
  │         executes            │              │               │            │
  │              │              │              │               │            │
  │              │   COMMAND_ACK MAVLink       │               │            │
  │              ├─────────────→│              │               │            │
  │              │              │              │               │            │
  │              │              │   Service response           │            │
  │              │              ├──────────────┼──────────────→│            │
  │              │              │              │               │            │
  │              │              │              │        MQTT result         │
  │              │              │              │               ├───────────→│
  │              │              │              │               │            │
  │              │              │              │               │      HTTP 200
  │              │              │              │               │            ├→ Frontend
```

### 9.2. Latences Typiques

| Étape | Latence Simulation | Latence Réelle | Notes |
|-------|-------------------|----------------|-------|
| Gazebo → PX4 (IMU) | < 1 ms | 0 ms | Direct (même hardware) |
| Gazebo → vision_bridge | 20 ms (50 Hz) | 5-30 ms | Dépend fréquence caméra |
| vision_bridge → MAVROS | < 1 ms | < 1 ms | ROS2 IPC (même machine) |
| MAVROS → PX4 (UDP) | < 1 ms | < 1 ms | Localhost |
| PX4 EKF2 cycle | 2.5 ms (400 Hz) | 2.5 ms | Constant |
| PX4 → MAVROS (UDP) | < 1 ms | < 1 ms | Localhost |
| MAVROS → mqtt_bridge | < 1 ms | < 1 ms | ROS2 IPC |
| mqtt_bridge → Backend | < 1 ms | 20-100 ms | Network (WiFi/4G) |
| Backend → Frontend | < 1 ms | 50-200 ms | WebSocket over internet |
| **TOTAL (sensor → display)** | **~30 ms** | **100-400 ms** | End-to-end |

**Commandé (user → drone)** :
| Étape | Latence Simulation | Latence Réelle |
|-------|-------------------|----------------|
| Frontend → Backend | < 1 ms | 50-200 ms |
| Backend → mqtt_bridge | < 1 ms | 20-100 ms |
| mqtt_bridge → MAVROS | < 1 ms | < 1 ms |
| MAVROS → PX4 | < 1 ms | < 1 ms |
| PX4 Commander validation | 10-50 ms | 10-50 ms |
| **TOTAL (click → execution)** | **~15 ms** | **100-400 ms** |

---

## 10. Glossaire

| Terme | Définition |
|-------|------------|
| **EKF2** | Extended Kalman Filter 2 : algorithme de fusion capteurs dans PX4 |
| **SITL** | Software In The Loop : simulation où firmware tourne sur PC (pas MCU) |
| **MAVLink** | Micro Air Vehicle Link : protocole binaire PX4 ↔ GCS/Companion |
| **MAVROS** | MAVLink + ROS : bridge officiel ROS2 ↔ PX4 |
| **Ground Truth** | Vérité terrain : valeur réelle exacte (connue en simulation) |
| **Odometry** | Estimation position/vitesse par intégration capteurs |
| **Body Frame** | Référentiel lié au drone (Forward-Right-Down) |
| **World Frame** | Référentiel absolu (East-North-Up en simulation) |
| **NED** | North-East-Down : frame PX4 (X=Nord, Y=Est, Z=Bas) |
| **ENU** | East-North-Up : frame ROS2 (X=Est, Y=Nord, Z=Haut) |
| **QoS** | Quality of Service : paramètres reliability/durability topics ROS2 |
| **Covariance** | Matrice d'incertitude (écart-type² pour chaque dimension) |
| **Innovation** | Différence entre mesure capteur et prédiction EKF |
| **Gain de Kalman** | Pondération optimale mesure vs prédiction dans EKF |
| **uORB** | Micro Object Request Broker : IPC interne PX4 |
| **GCS** | Ground Control Station : logiciel pilotage (QGroundControl) |

---

**Fin du document**

**Prochaines étapes** :
1. Lire ce document en entier pour comprendre l'architecture
2. Poser questions sur points peu clairs
3. Implémenter tests EKF2 avec ce référentiel
4. Corriger bugs multi-drone (namespacing)

**Questions fréquentes** :

**Q : Pourquoi EKF2 est dans PX4 et pas dans ROS2 ?**
R : EKF2 nécessite temps-réel strict (400 Hz IMU). PX4 tourne sur MCU dédié (Pixhawk) avec RTOS, garantit latence <2.5ms. ROS2 sur Linux (non-RT) ne peut garantir ça.

**Q : Peut-on avoir un seul MAVROS pour tous les drones ?**
R : Techniquement oui (multi-vehicle mode avec System ID filtering), mais complexe et non-standard. Recommandé : 1 MAVROS par drone.

**Q : Pourquoi transformer velocity en body frame ?**
R : PX4 EKF2 attend velocities dans body frame car cohérent avec IMU (mesure accélérations dans body frame). Simplifie fusion capteurs.

**Q : Quelle est la meilleure précision atteignable ?**
R : Simulation : ~2-5 cm. Réel avec T265 : ~10-20 cm indoor. Réel avec RTK-GPS : ~2 cm outdoor.
