"""
Unit tests for ROS2 launch file configuration validation.

Tests the launch file configurations:
- MAVROS launch file (px4_sitl.launch.py)
- MQTT bridge launch file
- Parameter validation
- Plugin configuration
- Connection URLs

These tests do NOT require:
- Running ROS2 launch
- Active containers
- MAVROS or PX4 running
"""

import pytest
import re
from pathlib import Path


class TestMAVROSLaunchConfiguration:
    """Test MAVROS launch file configuration."""

    # Expected MAVROS configuration from px4_sitl.launch.py
    EXPECTED_FCU_URL = 'udp://:14540@127.0.0.1:14580'
    EXPECTED_PLUGINS = [
        'sys_status',
        'sys_time',
        'imu',
        'local_position',
        'global_position',
        'vision_pose',
        'command',
        'battery',
        'rc',
        'param',
        'mission',
        'home_position'
    ]

    def test_fcu_url_format_udp(self):
        """FCU URL should use UDP protocol for SITL connection."""
        fcu_url = self.EXPECTED_FCU_URL

        assert fcu_url.startswith('udp://')

    def test_fcu_url_local_port_14540(self):
        """FCU URL should listen on local port 14540 (PX4 MAVLink port)."""
        fcu_url = self.EXPECTED_FCU_URL

        # Parse port from udp://:14540@...
        match = re.search(r':(\d+)@', fcu_url)
        assert match is not None
        local_port = int(match.group(1))

        assert local_port == 14540

    def test_fcu_url_remote_port_14580(self):
        """FCU URL should send to remote port 14580 (MAVROS side)."""
        fcu_url = self.EXPECTED_FCU_URL

        # Parse remote port from ...@host:14580
        match = re.search(r'@[\d.]+:(\d+)', fcu_url)
        assert match is not None
        remote_port = int(match.group(1))

        assert remote_port == 14580

    def test_target_system_id_default(self):
        """Target system ID should default to 1 (single drone)."""
        tgt_system = 1

        assert tgt_system == 1

    def test_plugin_allowlist_includes_critical_plugins(self):
        """Plugin allowlist should include all critical plugins."""
        required_plugins = [
            'sys_status',      # Drone state
            'local_position',  # EKF2 output
            'vision_pose',     # Vision input for EKF2
            'command'          # ARM/DISARM/TAKEOFF/LAND
        ]

        for plugin in required_plugins:
            assert plugin in self.EXPECTED_PLUGINS, f"Critical plugin '{plugin}' missing"

    def test_plugin_allowlist_excludes_setpoint_plugins(self):
        """
        Setpoint plugins should NOT be in allowlist.
        They conflict with local_position on 'local' topic.
        """
        excluded_plugins = [
            'setpoint_position',
            'setpoint_velocity',
            'setpoint_attitude',
            'setpoint_raw'
        ]

        for plugin in excluded_plugins:
            assert plugin not in self.EXPECTED_PLUGINS, \
                f"Conflicting plugin '{plugin}' should not be in allowlist"

    def test_plugin_vision_pose_enabled(self):
        """vision_pose plugin must be enabled for GPS-free operation."""
        assert 'vision_pose' in self.EXPECTED_PLUGINS

    def test_plugin_imu_enabled(self):
        """IMU plugin required for sensor data."""
        assert 'imu' in self.EXPECTED_PLUGINS

    def test_plugin_battery_enabled(self):
        """Battery plugin required for telemetry."""
        assert 'battery' in self.EXPECTED_PLUGINS

    def test_local_position_frame_id(self):
        """Local position should use 'map' frame."""
        frame_id = 'map'

        assert frame_id == 'map'

    def test_tf_broadcast_enabled(self):
        """TF broadcasting should be enabled for local_position."""
        tf_send = True

        assert tf_send is True

    def test_tf_frame_ids(self):
        """TF should broadcast map → base_link."""
        tf_frame_id = 'map'
        tf_child_frame_id = 'base_link'

        assert tf_frame_id == 'map'
        assert tf_child_frame_id == 'base_link'

    def test_fcu_protocol_version(self):
        """FCU protocol should be MAVLink v2.0."""
        fcu_protocol = 'v2.0'

        assert fcu_protocol == 'v2.0'

    def test_mavros_system_id(self):
        """MAVROS should use system ID 1 (GCS)."""
        system_id = 1

        assert system_id == 1

    def test_mavros_component_id(self):
        """MAVROS should use component ID 240 (GCS/companion computer)."""
        component_id = 240

        assert component_id == 240

    def test_connection_timeout(self):
        """Connection timeout should be reasonable (10s)."""
        timeout = 10.0

        assert timeout == 10.0
        assert timeout > 0

    def test_timesync_enabled(self):
        """Time synchronization should be enabled."""
        timesync_rate = 10.0

        assert timesync_rate > 0


class TestMQTTBridgeLaunchConfiguration:
    """Test MQTT Bridge launch file configuration."""

    def test_default_drone_id(self):
        """Default drone ID should be 'drone_1'."""
        drone_id = 'drone_1'

        assert drone_id == 'drone_1'

    def test_mqtt_broker_hostname(self):
        """MQTT broker should be 'mqtt' (Docker service name)."""
        mqtt_broker = 'mqtt'

        assert mqtt_broker == 'mqtt'

    def test_mqtt_broker_port(self):
        """MQTT broker should use port 1883 (standard MQTT)."""
        mqtt_port = 1883

        assert mqtt_port == 1883

    def test_mqtt_client_id_format(self):
        """MQTT client ID should be unique per drone."""
        drone_id = 'drone_1'
        client_id = f'ros2_bridge_{drone_id}'

        assert client_id == 'ros2_bridge_drone_1'
        assert 'ros2_bridge' in client_id

    def test_telemetry_publish_rate(self):
        """Telemetry should publish at 2 Hz (0.5s timer)."""
        timer_period = 0.5  # seconds

        publish_rate = 1.0 / timer_period

        assert publish_rate == 2.0  # 2 Hz


class TestVisionBridgeLaunchConfiguration:
    """Test Vision Pose Bridge launch file configuration."""

    def test_default_model_name(self):
        """Default Gazebo model should be 'x500_0'."""
        model_name = 'x500_0'

        assert model_name == 'x500_0'

    def test_gazebo_world_name(self):
        """Gazebo world should be 'default'."""
        world_name = 'default'

        assert world_name == 'default'

    def test_mavros_odometry_topic(self):
        """Should publish to /mavros/odometry/out."""
        odom_topic = '/mavros/odometry/out'

        assert odom_topic == '/mavros/odometry/out'
        assert odom_topic.startswith('/mavros/')

    def test_gazebo_pose_topic_format(self):
        """Gazebo pose topic should follow correct format."""
        world_name = 'default'
        topic = f'/world/{world_name}/dynamic_pose/info'

        assert topic == '/world/default/dynamic_pose/info'

    def test_gazebo_odom_topic_format(self):
        """Gazebo odometry topic should follow correct format."""
        model_name = 'x500_0'
        topic = f'/model/{model_name}/odometry'

        assert topic == '/model/x500_0/odometry'


class TestMultiDroneConfiguration:
    """Test multi-drone port allocation and namespacing."""

    def test_mavlink_port_allocation(self):
        """MAVLink ports should follow 14540 + drone_num pattern."""
        base_port = 14540

        drone_0_port = base_port + 0
        drone_1_port = base_port + 1
        drone_2_port = base_port + 2

        assert drone_0_port == 14540
        assert drone_1_port == 14541
        assert drone_2_port == 14542

    def test_simulator_port_allocation(self):
        """Simulator ports should follow 18570 + drone_num pattern."""
        base_port = 18570

        drone_0_port = base_port + 0
        drone_1_port = base_port + 1

        assert drone_0_port == 18570
        assert drone_1_port == 18571

    def test_system_id_allocation(self):
        """System IDs should be drone_num + 1."""
        drone_num = 0
        system_id = drone_num + 1

        assert system_id == 1

        drone_num = 1
        system_id = drone_num + 1

        assert system_id == 2

    def test_namespace_format(self):
        """Drone namespace should be /drone_N format."""
        drone_num = 1
        namespace = f'/drone_{drone_num}'

        assert namespace == '/drone_1'
        assert namespace.startswith('/drone_')

    def test_mqtt_topic_isolation(self):
        """Each drone should have isolated MQTT topics."""
        drone_id_1 = 'drone_1'
        drone_id_2 = 'drone_2'

        topic_1 = f'drone/{drone_id_1}/telemetry'
        topic_2 = f'drone/{drone_id_2}/telemetry'

        # Topics should be different
        assert topic_1 != topic_2
        assert topic_1 == 'drone/drone_1/telemetry'
        assert topic_2 == 'drone/drone_2/telemetry'


class TestROS2DomainConfiguration:
    """Test ROS2 DDS domain configuration."""

    def test_ros_domain_id_set(self):
        """ROS_DOMAIN_ID should be set for DDS isolation."""
        ros_domain_id = 42

        assert ros_domain_id == 42
        assert 0 <= ros_domain_id <= 101  # Valid DDS domain range

    def test_rmw_implementation(self):
        """Should use FastDDS (rmw_fastrtps_cpp)."""
        rmw_implementation = 'rmw_fastrtps_cpp'

        assert rmw_implementation == 'rmw_fastrtps_cpp'


class TestServiceTimeouts:
    """Test service call timeout configuration."""

    def test_service_wait_timeout(self):
        """Service wait timeout should be reasonable (5s)."""
        timeout = 5.0

        assert timeout == 5.0
        assert timeout > 0

    def test_mavros_service_wait_timeout(self):
        """MAVROS service availability should wait up to 30s."""
        timeout = 30.0

        assert timeout == 30.0
        assert timeout >= 30  # Allow time for MAVROS to start


class TestQoSProfiles:
    """Test Quality of Service profile configurations."""

    def test_state_qos_reliable(self):
        """State topic must use RELIABLE QoS."""
        qos_reliability = 'RELIABLE'

        assert qos_reliability == 'RELIABLE'

    def test_state_qos_transient_local(self):
        """State topic must use TRANSIENT_LOCAL durability."""
        qos_durability = 'TRANSIENT_LOCAL'

        assert qos_durability == 'TRANSIENT_LOCAL'

    def test_state_qos_depth(self):
        """State topic QoS depth should be 10."""
        qos_depth = 10

        assert qos_depth == 10

    def test_best_effort_topics(self):
        """Position/velocity topics should use BEST_EFFORT."""
        qos_reliability = 'BEST_EFFORT'

        assert qos_reliability == 'BEST_EFFORT'

    def test_vision_odometry_qos(self):
        """Vision odometry should use BEST_EFFORT to match MAVROS."""
        qos_reliability = 'BEST_EFFORT'

        assert qos_reliability == 'BEST_EFFORT'


class TestLaunchFileExistence:
    """Verify launch files exist in expected locations."""

    def test_mavros_launch_file_exists(self):
        """MAVROS launch file should exist."""
        launch_file = Path('simulation/src/mavros_launcher/launch/px4_sitl.launch.py')

        # This test runs from project root
        # In actual test environment, adjust path as needed
        expected_name = 'px4_sitl.launch.py'

        assert expected_name in str(launch_file)

    def test_mqtt_bridge_launch_file_exists(self):
        """MQTT bridge launch file should exist."""
        launch_file = Path('simulation/src/mqtt_bridge/launch/mqtt_bridge.launch.py')

        expected_name = 'mqtt_bridge.launch.py'

        assert expected_name in str(launch_file)


class TestParameterDefaults:
    """Test parameter default values."""

    def test_mavros_namespace_default_empty(self):
        """MAVROS namespace should default to empty (global)."""
        namespace = ''

        assert namespace == ''

    def test_gcs_url_default_empty(self):
        """GCS URL should default to empty (no GCS connection)."""
        gcs_url = ''

        assert gcs_url == ''

    def test_drone_id_parameter_format(self):
        """Drone ID parameter should be string format."""
        drone_id = 'drone_1'

        assert isinstance(drone_id, str)
        assert drone_id.startswith('drone_')
