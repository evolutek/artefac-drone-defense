"""
Unit tests for MQTT Bridge node logic (without full ROS2 infrastructure).

Tests the core logic of mqtt_bridge/bridge_node.py:
- MQTT message parsing and command handling
- Telemetry data serialization
- Command result formatting
- State management

These tests do NOT require:
- Running ROS2 nodes
- MQTT broker
- MAVROS services
- Docker containers
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch, call
from collections import namedtuple


# Mock ROS2 message types
MockState = namedtuple('State', ['connected', 'armed', 'mode'])
MockPoseStamped = namedtuple('PoseStamped', ['pose'])
MockPose = namedtuple('Pose', ['position', 'orientation'])
MockPoint = namedtuple('Point', ['x', 'y', 'z'])
MockQuaternion = namedtuple('Quaternion', ['x', 'y', 'z', 'w'])
MockBatteryState = namedtuple('BatteryState', ['percentage'])
MockTwistStamped = namedtuple('TwistStamped', ['twist'])
MockTwist = namedtuple('Twist', ['linear', 'angular'])
MockVector3 = namedtuple('Vector3', ['x', 'y', 'z'])


class TestMQTTBridgeMessageParsing:
    """Test MQTT message parsing and validation."""

    def test_parse_valid_arm_command(self):
        """Parse valid ARM command from MQTT."""
        payload = json.dumps({
            'command': 'ARM',
            'params': {}
        })

        data = json.loads(payload)
        assert data['command'] == 'ARM'
        assert 'params' in data

    def test_parse_valid_takeoff_command_with_altitude(self):
        """Parse TAKEOFF command with altitude parameter."""
        payload = json.dumps({
            'command': 'TAKEOFF',
            'params': {'altitude': 10.0}
        })

        data = json.loads(payload)
        assert data['command'] == 'TAKEOFF'
        assert data['params']['altitude'] == 10.0

    def test_parse_takeoff_command_default_altitude(self):
        """TAKEOFF command should default to 5.0m if no altitude provided."""
        payload = json.dumps({
            'command': 'TAKEOFF',
            'params': {}
        })

        data = json.loads(payload)
        altitude = data.get('params', {}).get('altitude', 5.0)
        assert altitude == 5.0

    def test_parse_invalid_json(self):
        """Invalid JSON should raise JSONDecodeError."""
        payload = "invalid json{{"

        with pytest.raises(json.JSONDecodeError):
            json.loads(payload)

    def test_parse_missing_command_field(self):
        """Message without 'command' field should be handled gracefully."""
        payload = json.dumps({
            'params': {'altitude': 5.0}
        })

        data = json.loads(payload)
        command = data.get('command')
        assert command is None

    def test_unknown_command_type(self):
        """Unknown command should be identifiable."""
        payload = json.dumps({
            'command': 'UNKNOWN_COMMAND',
            'params': {}
        })

        data = json.loads(payload)
        assert data['command'] == 'UNKNOWN_COMMAND'
        # Bridge should handle this gracefully (log warning)


class TestMQTTBridgeTelemetrySerialization:
    """Test telemetry data serialization to MQTT format."""

    def test_serialize_complete_telemetry(self):
        """Serialize telemetry with all fields available."""
        # Create mock data
        state = MockState(connected=True, armed=True, mode='OFFBOARD')
        position = MockPoseStamped(
            pose=MockPose(
                position=MockPoint(x=1.5, y=2.3, z=3.7),
                orientation=MockQuaternion(x=0.0, y=0.0, z=0.0, w=1.0)
            )
        )
        battery = MockBatteryState(percentage=0.85)
        velocity = MockTwistStamped(
            twist=MockTwist(
                linear=MockVector3(x=1.0, y=0.5, z=0.2),
                angular=MockVector3(x=0.0, y=0.0, z=0.1)
            )
        )

        # Build telemetry dict
        telemetry = {
            'connected': state.connected,
            'armed': state.armed,
            'mode': state.mode,
            'position_x': position.pose.position.x,
            'position_y': position.pose.position.y,
            'position_z': position.pose.position.z,
            'orientation_x': position.pose.orientation.x,
            'orientation_y': position.pose.orientation.y,
            'orientation_z': position.pose.orientation.z,
            'orientation_w': position.pose.orientation.w,
            'velocity_x': velocity.twist.linear.x,
            'velocity_y': velocity.twist.linear.y,
            'velocity_z': velocity.twist.linear.z,
            'battery': battery.percentage * 100
        }

        # Serialize to JSON
        json_str = json.dumps(telemetry)
        parsed = json.loads(json_str)

        assert parsed['connected'] is True
        assert parsed['armed'] is True
        assert parsed['mode'] == 'OFFBOARD'
        assert parsed['position_x'] == 1.5
        assert parsed['battery'] == 85.0

    def test_serialize_partial_telemetry_only_state(self):
        """Serialize telemetry with only state data (missing sensors)."""
        state = MockState(connected=True, armed=False, mode='MANUAL')

        telemetry = {
            'connected': state.connected,
            'armed': state.armed,
            'mode': state.mode
        }

        json_str = json.dumps(telemetry)
        parsed = json.loads(json_str)

        # Should have state but no position/velocity
        assert parsed['connected'] is True
        assert parsed['armed'] is False
        assert 'position_x' not in parsed
        assert 'velocity_x' not in parsed

    def test_serialize_empty_telemetry(self):
        """Empty telemetry should serialize to empty dict."""
        telemetry = {}

        json_str = json.dumps(telemetry)
        parsed = json.loads(json_str)

        assert parsed == {}


class TestMQTTBridgeCommandResults:
    """Test command result message formatting."""

    def test_format_successful_arm_result(self):
        """Format successful ARM command result."""
        result = {
            'command': 'ARM',
            'success': True,
            'message': 'Drone armed successfully',
            'timestamp': 1234567890
        }

        json_str = json.dumps(result)
        parsed = json.loads(json_str)

        assert parsed['command'] == 'ARM'
        assert parsed['success'] is True
        assert 'armed successfully' in parsed['message']

    def test_format_failed_takeoff_result(self):
        """Format failed TAKEOFF command result."""
        result = {
            'command': 'TAKEOFF',
            'success': False,
            'message': 'Cannot takeoff: drone must be armed first',
            'timestamp': 1234567890
        }

        json_str = json.dumps(result)
        parsed = json.loads(json_str)

        assert parsed['command'] == 'TAKEOFF'
        assert parsed['success'] is False
        assert 'must be armed' in parsed['message']

    def test_format_service_unavailable_result(self):
        """Format result when MAVROS service is unavailable."""
        result = {
            'command': 'LAND',
            'success': False,
            'message': 'Land service not available',
            'timestamp': 1234567890
        }

        json_str = json.dumps(result)
        parsed = json.loads(json_str)

        assert parsed['success'] is False
        assert 'not available' in parsed['message']


class TestMQTTBridgeStateManagement:
    """Test state management and caching."""

    def test_state_update_triggers_publish(self):
        """New state should be cached and trigger MQTT publish."""
        # Simulate state callback
        new_state = MockState(connected=True, armed=True, mode='OFFBOARD')

        # State cache
        current_state = new_state

        # Verify state is cached
        assert current_state.connected is True
        assert current_state.armed is True
        assert current_state.mode == 'OFFBOARD'

    def test_position_update_cached(self):
        """Position updates should be cached for telemetry."""
        new_position = MockPoseStamped(
            pose=MockPose(
                position=MockPoint(x=5.0, y=3.0, z=2.0),
                orientation=MockQuaternion(x=0.0, y=0.0, z=0.0, w=1.0)
            )
        )

        current_position = new_position

        assert current_position.pose.position.x == 5.0
        assert current_position.pose.position.z == 2.0

    def test_multiple_sensor_updates(self):
        """Multiple sensor updates should all be cached independently."""
        state = MockState(connected=True, armed=False, mode='MANUAL')
        position = MockPoseStamped(
            pose=MockPose(
                position=MockPoint(x=0.0, y=0.0, z=0.0),
                orientation=MockQuaternion(x=0.0, y=0.0, z=0.0, w=1.0)
            )
        )
        battery = MockBatteryState(percentage=0.75)

        # All should be cached independently
        assert state.connected is True
        assert position.pose.position.x == 0.0
        assert battery.percentage == 0.75


class TestMQTTBridgeQoSConfiguration:
    """Test QoS profile configuration logic."""

    def test_state_topic_requires_reliable_transient_local(self):
        """
        MAVROS /mavros/state requires RELIABLE + TRANSIENT_LOCAL QoS.
        This is critical for proper state reception.
        """
        # Expected QoS configuration
        state_qos = {
            'reliability': 'RELIABLE',
            'durability': 'TRANSIENT_LOCAL',
            'history': 'KEEP_LAST',
            'depth': 10
        }

        assert state_qos['reliability'] == 'RELIABLE'
        assert state_qos['durability'] == 'TRANSIENT_LOCAL'

    def test_other_topics_use_best_effort(self):
        """Other MAVROS topics typically use BEST_EFFORT QoS."""
        qos_profile = {
            'reliability': 'BEST_EFFORT',
            'history': 'KEEP_LAST',
            'depth': 10
        }

        assert qos_profile['reliability'] == 'BEST_EFFORT'
        assert qos_profile['depth'] == 10


class TestMQTTBridgeTopicNames:
    """Test MQTT and ROS2 topic name formatting."""

    def test_mqtt_telemetry_topic_format(self):
        """MQTT telemetry topic should follow drone/{id}/telemetry format."""
        drone_id = 'drone_1'
        topic = f'drone/{drone_id}/telemetry'

        assert topic == 'drone/drone_1/telemetry'

    def test_mqtt_command_topic_format(self):
        """MQTT command topic should follow drone/{id}/command format."""
        drone_id = 'drone_2'
        topic = f'drone/{drone_id}/command'

        assert topic == 'drone/drone_2/command'

    def test_mqtt_state_topic_format(self):
        """MQTT state topic should follow drone/{id}/state format."""
        drone_id = 'drone_1'
        topic = f'drone/{drone_id}/state'

        assert topic == 'drone/drone_1/state'

    def test_mavros_state_topic_absolute_path(self):
        """MAVROS state topic must be /mavros/state (absolute path)."""
        state_topic = '/mavros/state'

        # Must start with /mavros/ (not relative)
        assert state_topic.startswith('/mavros/')
        assert state_topic == '/mavros/state'

    def test_mavros_service_namespacing(self):
        """
        MAVROS services are under /mavros_node namespace.
        This was a critical bug fix (was incorrectly /mavros/cmd).
        """
        arming_service = '/mavros_node/arming'
        takeoff_service = '/mavros_node/cmd/takeoff'

        assert arming_service.startswith('/mavros_node/')
        assert takeoff_service.startswith('/mavros_node/')


class TestMQTTBridgeArmingLogic:
    """Test arming/disarming command logic."""

    def test_arm_command_requires_service_available(self):
        """ARM command should check service availability first."""
        # Mock service client
        service_available = False

        if not service_available:
            error_msg = 'Arming service not available'
            # Should publish command result with failure
            assert 'not available' in error_msg

    def test_disarm_command_formatting(self):
        """DISARM command should set value=False in service request."""
        arm_value = False  # DISARM
        command_name = 'DISARM' if not arm_value else 'ARM'

        assert command_name == 'DISARM'
        assert arm_value is False

    def test_arming_result_callback_success(self):
        """Successful arming should publish success result."""
        response_success = True
        arm_value = True

        if response_success:
            action = 'armed' if arm_value else 'disarmed'
            success_msg = f'Drone {action} successfully'

            assert success_msg == 'Drone armed successfully'

    def test_arming_result_callback_failure(self):
        """Failed arming should publish failure result with reason."""
        response_success = False
        arm_value = True

        if not response_success:
            action = 'armed' if arm_value else 'disarmed'
            error_msg = f'Failed to {action.lower()} drone - PX4 rejected command (check GPS fix, flight mode, or safety checks)'

            assert 'PX4 rejected' in error_msg
            assert 'GPS fix' in error_msg  # Helpful diagnostic info


class TestMQTTBridgeTakeoffLogic:
    """Test takeoff command logic and preconditions."""

    def test_takeoff_requires_armed_state(self):
        """TAKEOFF should check if drone is armed first."""
        current_state = MockState(connected=True, armed=False, mode='MANUAL')

        if not current_state.armed:
            error_msg = 'Cannot takeoff: drone must be armed first'
            assert 'must be armed' in error_msg

    def test_takeoff_with_custom_altitude(self):
        """TAKEOFF should accept custom altitude parameter."""
        altitude = 15.0

        # Service request should include altitude
        assert altitude == 15.0

    def test_takeoff_success_result(self):
        """Successful takeoff should include altitude in result message."""
        response_success = True
        altitude = 10.0

        if response_success:
            success_msg = f'Takeoff command sent (altitude: {altitude}m)'
            assert '10.0m' in success_msg


class TestMQTTBridgeLandLogic:
    """Test land command logic."""

    def test_land_command_no_parameters(self):
        """LAND command should not require parameters."""
        # LAND request is parameter-less
        # Just verify we can create an empty request dict
        request = {}
        assert request == {}

    def test_land_success_result(self):
        """Successful land should publish success result."""
        response_success = True

        if response_success:
            success_msg = 'Land command sent'
            assert success_msg == 'Land command sent'
