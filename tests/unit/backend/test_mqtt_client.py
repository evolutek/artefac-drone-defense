"""
Unit tests for MQTT Client
Tests MQTT connection, message handling, and command publishing
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import json
import time
import threading
from datetime import datetime
from backend.app.mqtt_client import MQTTClient
from backend.app import crud


# ==================== Shared Test Helpers ====================

class MQTTTestHelpers:
    """Shared helpers for MQTT tests"""

    @staticmethod
    def create_mock_message(topic, payload_dict):
        """Create a mock MQTT message"""
        msg = Mock()
        msg.topic = topic
        msg.payload = json.dumps(payload_dict).encode()
        return msg

    @staticmethod
    def setup_successful_command(mock_client):
        """Setup mock for successful command execution"""
        result = Mock()
        result.rc = 0  # MQTT_ERR_SUCCESS
        mock_client.publish.return_value = result


# ==================== Connection Tests ====================

@patch('paho.mqtt.client.Client')
def test_mqtt_start_success(mock_client_class, mock_mqtt_client):
    """Test successful MQTT client start"""
    mock_instance = MagicMock()
    mock_client_class.return_value = mock_instance
    mqtt = MQTTClient()

    mqtt.start()

    mock_client_class.assert_called_once_with(client_id="backend_mqtt_client")
    mock_instance.connect.assert_called_once_with("localhost", 1883, keepalive=60)
    mock_instance.loop_start.assert_called_once()
    assert mqtt.client is not None


@patch('paho.mqtt.client.Client')
def test_mqtt_start_already_started(mock_client_class):
    """Test starting MQTT client when already started"""
    mqtt = MQTTClient()
    mqtt.client = MagicMock()

    mqtt.start()

    # Should not create a new client
    mock_client_class.assert_not_called()


@patch('paho.mqtt.client.Client')
def test_mqtt_start_connection_failure(mock_client_class):
    """Test MQTT start with connection failure"""
    mock_instance = MagicMock()
    mock_instance.connect.side_effect = Exception("Connection refused")
    mock_client_class.return_value = mock_instance
    mqtt = MQTTClient()

    mqtt.start()

    # Client should be None after failure
    assert mqtt.client is None


@pytest.mark.parametrize("initially_connected", [True, False])
def test_mqtt_stop(mock_mqtt_client, initially_connected):
    """Test stopping MQTT client"""
    mqtt = MQTTClient()
    mqtt.client = mock_mqtt_client if initially_connected else None
    mqtt.connected = initially_connected

    mqtt.stop()

    if initially_connected:
        mock_mqtt_client.loop_stop.assert_called_once()
        mock_mqtt_client.disconnect.assert_called_once()
    assert mqtt.client is None
    assert mqtt.connected is False


def test_mqtt_is_connected():
    """Test checking MQTT connection status"""
    mqtt = MQTTClient()

    # Initially disconnected
    assert mqtt.is_connected() is False

    # Simulate connection
    mqtt.connected = True
    assert mqtt.is_connected() is True


# ==================== Callback Tests ====================

@pytest.mark.parametrize("rc,expected_connected,expected_subscriptions", [
    (0, True, 3),  # Success
    (1, False, 0),  # Failure
])
def test_on_connect(mock_mqtt_client, rc, expected_connected, expected_subscriptions):
    """Test connection callback with success and failure"""
    mqtt = MQTTClient()

    mqtt.on_connect(mock_mqtt_client, None, None, rc)

    assert mqtt.connected is expected_connected
    assert mock_mqtt_client.subscribe.call_count == expected_subscriptions

    if expected_connected:
        calls = mock_mqtt_client.subscribe.call_args_list
        assert call("drone/+/telemetry") in calls
        assert call("drone/+/state") in calls
        assert call("drone/+/command_result") in calls


@pytest.mark.parametrize("rc,disconnect_type", [
    (0, "expected"),
    (1, "unexpected"),
])
def test_on_disconnect(mock_mqtt_client, rc, disconnect_type):
    """Test disconnect callback"""
    mqtt = MQTTClient()
    mqtt.connected = True

    mqtt.on_disconnect(mock_mqtt_client, None, rc)

    assert mqtt.connected is False


# ==================== Message Handling Tests ====================

def test_on_message_telemetry(db_session):
    """Test handling telemetry message"""
    mqtt = MQTTClient()
    mqtt.telemetry_callback = Mock()

    # Create test drone
    crud.create_drone(db_session, drone_id="drone_1")
    db_session.commit()

    msg = MQTTTestHelpers.create_mock_message(
        "drone/drone_1/telemetry",
        {
            "position_x": 1.5,
            "position_y": 2.3,
            "position_z": 5.0,
            "battery": 85.5,
            "velocity_x": 0.1,
            "velocity_y": 0.2,
            "velocity_z": 0.0
        }
    )

    # Patch SessionLocal at the source
    mock_session_factory = Mock(return_value=db_session)
    with patch('backend.app.models.database.SessionLocal', mock_session_factory):
        mqtt.on_message(None, None, msg)

    # Assert: Telemetry stored in database
    telemetry = crud.get_latest_telemetry(db_session, "drone_1")
    assert telemetry is not None
    assert telemetry.position_x == 1.5
    assert telemetry.battery_level == 85.5

    # Assert: Callback triggered
    mqtt.telemetry_callback.assert_called_once()


def test_on_message_state(db_session):
    """Test handling state message"""
    mqtt = MQTTClient()
    mqtt.state_callback = Mock()

    crud.create_drone(db_session, drone_id="drone_1")
    db_session.commit()

    msg = MQTTTestHelpers.create_mock_message(
        "drone/drone_1/state",
        {
            "connected": True,
            "armed": True,
            "mode": "OFFBOARD"
        }
    )

    mock_session_factory = Mock(return_value=db_session)
    with patch('backend.app.models.database.SessionLocal', mock_session_factory):
        mqtt.on_message(None, None, msg)

    # Assert: State updated in database
    drone = crud.get_drone(db_session, "drone_1")
    assert drone.is_armed is True
    assert drone.flight_mode == "OFFBOARD"
    assert drone.status == "armed"

    mqtt.state_callback.assert_called_once()


def test_on_message_command_result():
    """Test handling command result message"""
    mqtt = MQTTClient()
    mqtt.command_result_callback = Mock()

    msg = MQTTTestHelpers.create_mock_message(
        "drone/drone_1/command_result",
        {
            "command": "ARM",
            "success": True,
            "message": "Drone armed successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    mqtt.on_message(None, None, msg)

    # Assert: Result stored
    assert "drone_1" in mqtt.command_results
    assert "ARM" in mqtt.command_results["drone_1"]
    assert mqtt.command_results["drone_1"]["ARM"]["success"] is True

    mqtt.command_result_callback.assert_called_once()


@pytest.mark.parametrize("invalid_input", [
    ("invalid/topic/format/extra", b"{}"),  # Invalid topic format
    ("drone/drone_1/telemetry", b"not valid json"),  # Invalid JSON
])
def test_on_message_invalid_input(invalid_input):
    """Test handling messages with invalid input"""
    mqtt = MQTTClient()

    topic, payload = invalid_input
    msg = Mock()
    msg.topic = topic
    msg.payload = payload

    # Should not raise error
    mqtt.on_message(None, None, msg)


def test_on_message_auto_register_drone(db_session):
    """Test auto-registration of unknown drone on telemetry"""
    mqtt = MQTTClient()

    msg = MQTTTestHelpers.create_mock_message(
        "drone/new_drone/telemetry",
        {
            "position_x": 0.0,
            "position_y": 0.0,
            "position_z": 0.0,
            "battery": 100.0
        }
    )

    mock_session_factory = Mock(return_value=db_session)
    with patch('backend.app.models.database.SessionLocal', mock_session_factory):
        mqtt.on_message(None, None, msg)

    # Assert: Drone auto-registered
    drone = crud.get_drone(db_session, "new_drone")
    assert drone is not None
    assert drone.drone_id == "new_drone"


# ==================== Command Publishing Tests ====================

@pytest.mark.parametrize("command,params,expected_payload_keys", [
    ("ARM", None, ["command", "timestamp"]),
    ("TAKEOFF", {"altitude": 10.0}, ["command", "params", "timestamp"]),
])
def test_publish_command_success(mock_mqtt_client, command, params, expected_payload_keys):
    """Test successful command publishing"""
    import paho.mqtt.client as mqtt_module

    mqtt_instance = MQTTClient()
    mqtt_instance.client = mock_mqtt_client
    mqtt_instance.connected = True

    MQTTTestHelpers.setup_successful_command(mock_mqtt_client)

    success = mqtt_instance.publish_command("drone_1", command, params)

    assert success is True
    mock_mqtt_client.publish.assert_called_once()
    args, kwargs = mock_mqtt_client.publish.call_args
    assert args[0] == "drone/drone_1/command"

    payload = json.loads(args[1])
    for key in expected_payload_keys:
        assert key in payload
    assert payload["command"] == command
    if params:
        assert payload["params"] == params
    assert kwargs["qos"] == 1


@pytest.mark.parametrize("failure_scenario", [
    "not_connected",
    "publish_failure",
    "exception",
])
def test_publish_command_failures(mock_mqtt_client, failure_scenario):
    """Test command publishing failure scenarios"""
    mqtt_instance = MQTTClient()

    if failure_scenario == "not_connected":
        mqtt_instance.connected = False
    elif failure_scenario == "publish_failure":
        mqtt_instance.client = mock_mqtt_client
        mqtt_instance.connected = True
        result = Mock()
        result.rc = 1  # Not MQTT_ERR_SUCCESS
        mock_mqtt_client.publish.return_value = result
    elif failure_scenario == "exception":
        mqtt_instance.client = mock_mqtt_client
        mqtt_instance.connected = True
        mock_mqtt_client.publish.side_effect = Exception("Network error")

    success = mqtt_instance.publish_command("drone_1", "ARM")
    assert success is False


# ==================== Wait for Command Result Tests ====================

def test_wait_for_command_result_success():
    """Test waiting for command result that arrives quickly"""
    mqtt = MQTTClient()

    def add_result():
        time.sleep(0.05)
        mqtt.command_results = {
            "drone_1": {
                "ARM": {
                    "success": True,
                    "message": "Armed successfully",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        }

    thread = threading.Thread(target=add_result)
    thread.start()

    result = mqtt.wait_for_command_result("drone_1", "ARM", timeout=1.0)
    thread.join()

    assert result is not None
    assert result["success"] is True
    assert result["message"] == "Armed successfully"
    # Result should be cleaned up
    assert "ARM" not in mqtt.command_results.get("drone_1", {})


def test_wait_for_command_result_timeout():
    """Test waiting for command result that never arrives"""
    mqtt = MQTTClient()
    mqtt.command_results = {}

    start_time = time.time()
    result = mqtt.wait_for_command_result("drone_1", "ARM", timeout=0.2)
    elapsed = time.time() - start_time

    assert result is None
    assert elapsed >= 0.2
    assert elapsed < 0.5  # Should not wait much longer than timeout


def test_wait_for_command_result_clears_previous():
    """Test that waiting clears previous result"""
    mqtt = MQTTClient()
    mqtt.command_results = {
        "drone_1": {
            "ARM": {
                "success": False,
                "message": "Old result"
            }
        }
    }

    result = mqtt.wait_for_command_result("drone_1", "ARM", timeout=0.1)

    # Should timeout and not return old result
    assert result is None


def test_wait_for_command_result_arrives_during_wait():
    """Test result arriving while waiting"""
    mqtt = MQTTClient()
    mqtt.command_results = {}

    def simulate_result_arrival():
        time.sleep(0.1)
        mqtt.command_results["drone_1"] = {
            "ARM": {
                "success": True,
                "message": "Armed"
            }
        }

    thread = threading.Thread(target=simulate_result_arrival)
    thread.start()

    result = mqtt.wait_for_command_result("drone_1", "ARM", timeout=1.0)
    thread.join()

    assert result is not None
    assert result["success"] is True
