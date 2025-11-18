# ROS2 Workspace Source

This directory contains ROS2 packages for the drone simulation.

## Packages

### mavros_launcher

MAVROS launch files for connecting to PX4 SITL simulation.

**Package structure:**
```
mavros_launcher/
├── CMakeLists.txt          # Build configuration
├── package.xml             # Package metadata and dependencies
├── mavros_launcher/        # Python module
│   └── __init__.py
└── launch/                 # Launch files
    └── px4_sitl.launch.py  # Main MAVROS launch file for PX4 SITL
```

**Usage:**

Launch MAVROS with default settings (connects to tcp://127.0.0.1:4560):
```bash
ros2 launch mavros_launcher px4_sitl.launch.py
```

Launch with custom FCU URL:
```bash
ros2 launch mavros_launcher px4_sitl.launch.py fcu_url:=tcp://localhost:4560
```

Launch with namespace (for multi-drone):
```bash
ros2 launch mavros_launcher px4_sitl.launch.py namespace:=drone_0
```

**Available launch arguments:**
- `fcu_url` (default: tcp://127.0.0.1:4560) - FCU connection URL
- `gcs_url` (default: '') - GCS connection URL (optional)
- `tgt_system` (default: 1) - Target system ID
- `tgt_component` (default: 1) - Target component ID
- `namespace` (default: '') - Namespace for MAVROS topics

**Published topics:**
- `/mavros/state` - Connection state
- `/mavros/local_position/pose` - Local position
- `/mavros/global_position/global` - Global position (GPS)
- `/mavros/battery` - Battery status
- `/mavros/imu/data` - IMU data
- And more... (see MAVROS documentation)

## Adding New Packages

To add a new ROS2 package:

1. Create package directory:
   ```bash
   cd simulation/src
   ros2 pkg create --build-type ament_cmake my_package
   ```

2. Add your nodes, launch files, etc.

3. Rebuild workspace:
   ```bash
   cd /root/ros2_ws
   colcon build --symlink-install
   ```

## Building

The workspace is automatically built when the `ros2_integration` Docker container starts.

To manually rebuild:
```bash
docker compose exec ros2_integration bash
cd /root/ros2_ws
colcon build --symlink-install
source install/setup.bash
```
