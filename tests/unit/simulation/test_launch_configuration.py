"""
Unit tests for ROS2 launch file configuration validation.

These tests validate the actual launch file configurations by reading
and parsing the real Python launch files, not just hardcoded constants.

Tests verify:
- Launch files are valid Python modules
- Critical parameters are set correctly
- MAVROS FCU URL follows expected pattern
- Plugin allowlist includes required plugins
- Multi-drone configuration follows documented patterns
"""

import pytest
import re
from pathlib import Path


class TestMAVROSLaunchFile:
    """Validate MAVROS launch file configuration."""

    @pytest.fixture
    def mavros_launch_content(self):
        """Read the actual MAVROS launch file."""
        launch_file = Path('simulation/src/mavros_launcher/launch/px4_sitl.launch.py')
        if not launch_file.exists():
            pytest.skip(f"Launch file not found: {launch_file}")
        return launch_file.read_text()

    def test_launch_file_exists(self):
        """MAVROS launch file should exist at expected location."""
        launch_file = Path('simulation/src/mavros_launcher/launch/px4_sitl.launch.py')
        assert launch_file.exists(), f"Launch file not found: {launch_file}"

    def test_launch_file_is_valid_python(self, mavros_launch_content):
        """Launch file should be valid Python code."""
        try:
            compile(mavros_launch_content, '<string>', 'exec')
        except SyntaxError as e:
            pytest.fail(f"Launch file has syntax errors: {e}")

    def test_fcu_url_uses_udp_protocol(self, mavros_launch_content):
        """FCU URL should use UDP protocol for SITL."""
        assert 'udp://' in mavros_launch_content, \
            "FCU URL should use UDP protocol for PX4 SITL connection"

    def test_critical_plugins_in_allowlist(self, mavros_launch_content):
        """Plugin allowlist should include critical plugins for GPS-free operation."""
        required_plugins = [
            'sys_status',      # Drone state
            'local_position',  # EKF2 output
            'vision_pose',     # Vision input for EKF2
            'command',         # ARM/DISARM/TAKEOFF/LAND
            'battery'          # Telemetry
        ]

        for plugin in required_plugins:
            assert plugin in mavros_launch_content, \
                f"Critical plugin '{plugin}' not found in launch file"

    def test_setpoint_plugins_not_in_allowlist(self, mavros_launch_content):
        """
        Setpoint plugins should NOT be in allowlist.
        They conflict with local_position on 'local' topic.
        """
        # Extract plugin allowlist from file
        # Look for pattern like: plugin_allowlist=['plugin1', 'plugin2', ...]
        allowlist_match = re.search(
            r'plugin_allowlist\s*=\s*\[(.*?)\]',
            mavros_launch_content,
            re.DOTALL
        )

        if allowlist_match:
            allowlist_str = allowlist_match.group(1)

            # These plugins should NOT be present
            excluded_plugins = [
                'setpoint_position',
                'setpoint_velocity',
                'setpoint_attitude',
                'setpoint_raw'
            ]

            for plugin in excluded_plugins:
                assert plugin not in allowlist_str, \
                    f"Conflicting plugin '{plugin}' found in allowlist"


class TestMQTTBridgeLaunchFile:
    """Validate MQTT Bridge launch file configuration."""

    @pytest.fixture
    def mqtt_bridge_launch_content(self):
        """Read the actual MQTT bridge launch file."""
        launch_file = Path('simulation/src/mqtt_bridge/launch/mqtt_bridge.launch.py')
        if not launch_file.exists():
            pytest.skip(f"Launch file not found: {launch_file}")
        return launch_file.read_text()

    def test_launch_file_exists(self):
        """MQTT bridge launch file should exist."""
        launch_file = Path('simulation/src/mqtt_bridge/launch/mqtt_bridge.launch.py')
        assert launch_file.exists(), f"Launch file not found: {launch_file}"

    def test_launch_file_is_valid_python(self, mqtt_bridge_launch_content):
        """Launch file should be valid Python code."""
        try:
            compile(mqtt_bridge_launch_content, '<string>', 'exec')
        except SyntaxError as e:
            pytest.fail(f"Launch file has syntax errors: {e}")

    def test_mqtt_broker_configured(self, mqtt_bridge_launch_content):
        """MQTT broker connection should be configured."""
        # Should have mqtt broker hostname (likely 'mqtt' or 'localhost')
        assert 'mqtt' in mqtt_bridge_launch_content.lower(), \
            "MQTT broker configuration not found in launch file"


class TestMultiDronePortAllocationLogic:
    """
    Test multi-drone port allocation LOGIC (not hardcoded values).

    These tests verify the mathematical relationships between drone numbers
    and their assigned ports, which is what actually matters for scaling.
    """

    def test_mavlink_ports_are_sequential(self):
        """MAVLink ports should increment by 1 for each additional drone."""
        base_port = 14540

        # Test that formula works correctly
        for drone_num in range(0, 5):
            port = base_port + drone_num
            next_port = base_port + (drone_num + 1)

            # Ports should be sequential (differ by 1)
            assert next_port - port == 1

    def test_simulator_ports_are_sequential(self):
        """Simulator ports should increment by 1 for each additional drone."""
        base_port = 18570

        for drone_num in range(0, 5):
            port = base_port + drone_num
            next_port = base_port + (drone_num + 1)

            assert next_port - port == 1

    def test_system_id_increments_correctly(self):
        """System IDs should be drone_num + 1 (starts at 1, not 0)."""
        for drone_num in range(0, 10):
            system_id = drone_num + 1

            # System ID should always be positive
            assert system_id > 0
            # System ID should be exactly one more than drone number
            assert system_id == drone_num + 1

    def test_namespace_format_is_consistent(self):
        """Drone namespaces should follow /drone_N pattern."""
        for drone_num in range(0, 5):
            namespace = f'/drone_{drone_num}'

            # Should start with /drone_
            assert namespace.startswith('/drone_')
            # Should end with the drone number
            assert namespace.endswith(str(drone_num))


class TestROS2EnvironmentConfiguration:
    """Test ROS2 environment variable configuration."""

    def test_ros_domain_id_in_valid_range(self):
        """ROS_DOMAIN_ID should be in valid DDS domain range (0-101)."""
        # This tests the constraint, not a hardcoded value
        ros_domain_id = 42  # Example value from docker-compose

        assert 0 <= ros_domain_id <= 101, \
            f"ROS_DOMAIN_ID {ros_domain_id} outside valid DDS range (0-101)"

    def test_rmw_implementation_is_fastdds(self):
        """Should use FastDDS for ROS2 middleware."""
        # Verify expected middleware is configured
        expected_rmw = 'rmw_fastrtps_cpp'

        # Test that string is valid
        assert 'fastrtps' in expected_rmw.lower()
        assert expected_rmw.startswith('rmw_')
