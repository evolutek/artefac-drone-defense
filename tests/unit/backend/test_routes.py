"""
Unit tests for FastAPI routes
Tests all REST endpoints with mocked dependencies (DB and MQTT)
"""
import pytest
from unittest.mock import Mock


# ==================== Shared Test Helpers ====================

class RouteAssertions:
    """Shared assertion helpers for route tests"""

    @staticmethod
    def assert_not_found(response):
        """Assert 404 response"""
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @staticmethod
    def assert_success(response, status_code=200):
        """Assert successful response"""
        assert response.status_code == status_code
        return response.json()

    @staticmethod
    def assert_mqtt_unavailable(response):
        """Assert 503 MQTT broker unavailable"""
        assert response.status_code == 503
        assert "mqtt broker" in response.json()["detail"].lower()

    @staticmethod
    def assert_timeout(response):
        """Assert 504 command timeout"""
        assert response.status_code == 504
        assert "timeout" in response.json()["detail"].lower()

    @staticmethod
    def assert_command_failed(response):
        """Assert 400 command execution failed"""
        assert response.status_code == 400


# ==================== Health Check Tests ====================

@pytest.mark.parametrize("mqtt_connected,drones_count", [
    (True, 2),
    (False, 0),
])
def test_health_check(test_client, mock_mqtt_client_instance, create_test_drone, mqtt_connected, drones_count):
    """Test health check endpoint with various scenarios"""
    # Setup MQTT state
    mock_mqtt_client_instance.is_connected = Mock(return_value=mqtt_connected)

    # Setup drones
    if drones_count > 0:
        for i in range(1, drones_count + 1):
            create_test_drone(drone_id=f"drone_{i}", status="connected" if i == 1 else "armed")

    response = test_client.get("/health")
    data = RouteAssertions.assert_success(response)

    assert data["status"] == "healthy"
    assert data["mqtt_connected"] is mqtt_connected
    assert data["database"] == "operational"
    assert data["drones_connected"] == drones_count
    assert "timestamp" in data


# ==================== Drone CRUD Tests ====================

def test_register_drone_success(test_client):
    """Test successful drone registration"""
    response = test_client.post(
        "/drones",
        json={"drone_id": "drone_test", "name": "Test Drone", "model": "gz_x500"}
    )

    data = RouteAssertions.assert_success(response)
    assert data["drone_id"] == "drone_test"
    assert data["name"] == "Test Drone"
    assert data["model"] == "gz_x500"
    assert data["status"] == "disconnected"
    assert data["is_armed"] is False


def test_register_drone_duplicate(test_client, create_test_drone):
    """Test registering a drone that already exists"""
    create_test_drone(drone_id="drone_1")

    response = test_client.post(
        "/drones",
        json={"drone_id": "drone_1", "name": "Duplicate", "model": "gz_x500"}
    )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_list_drones_multiple(test_client, create_test_drone):
    """Test listing multiple drones"""
    create_test_drone(drone_id="drone_1", name="Drone 1")
    create_test_drone(drone_id="drone_2", name="Drone 2")
    create_test_drone(drone_id="drone_3", name="Drone 3")

    response = test_client.get("/drones")
    data = RouteAssertions.assert_success(response)

    assert len(data) == 3
    assert data[0]["drone_id"] == "drone_1"


def test_list_drones_pagination(test_client, create_test_drone):
    """Test drone listing pagination"""
    for i in range(1, 6):
        create_test_drone(drone_id=f"drone_{i}")

    response = test_client.get("/drones?skip=2&limit=2")
    data = RouteAssertions.assert_success(response)

    assert len(data) == 2
    assert data[0]["drone_id"] == "drone_3"
    assert data[1]["drone_id"] == "drone_4"


@pytest.mark.parametrize("drone_id,expected_result", [
    ("drone_1", "found"),
    ("nonexistent", "not_found"),
])
def test_get_drone(test_client, create_test_drone, drone_id, expected_result):
    """Test getting specific drone by ID"""
    create_test_drone(drone_id="drone_1", name="Test Drone")

    response = test_client.get(f"/drones/{drone_id}")

    if expected_result == "not_found":
        RouteAssertions.assert_not_found(response)
    else:
        data = RouteAssertions.assert_success(response)
        assert data["drone_id"] == "drone_1"
        assert data["name"] == "Test Drone"


def test_get_drone_telemetry_success(test_client, create_test_drone, create_test_telemetry):
    """Test getting drone telemetry"""
    create_test_drone(drone_id="drone_1")
    create_test_telemetry(
        drone_id="drone_1",
        position_x=1.5,
        position_y=2.3,
        position_z=5.0,
        battery_level=85.5
    )

    response = test_client.get("/drones/drone_1/telemetry")
    data = RouteAssertions.assert_success(response)

    assert data["drone_id"] == "drone_1"
    assert data["position_x"] == 1.5
    assert data["position_y"] == 2.3
    assert data["position_z"] == 5.0
    assert data["battery_level"] == 85.5


def test_get_drone_telemetry_not_found(test_client, create_test_drone):
    """Test getting telemetry for drone with no data"""
    create_test_drone(drone_id="drone_1")

    response = test_client.get("/drones/drone_1/telemetry")

    assert response.status_code == 404
    assert "no telemetry" in response.json()["detail"].lower()


# ==================== Command Tests (ARM/DISARM/TAKEOFF/LAND) ====================

@pytest.mark.parametrize("command,endpoint,mqtt_call_params", [
    ("ARM", "/drones/{}/arm", None),
    ("DISARM", "/drones/{}/disarm", None),
    ("TAKEOFF", "/drones/{}/takeoff?altitude=10.0", {"altitude": 10.0}),
    ("TAKEOFF", "/drones/{}/takeoff", {"altitude": 5.0}),  # Default altitude
    ("LAND", "/drones/{}/land", None),
])
def test_drone_command_success(test_client, create_test_drone, mock_mqtt_client_instance,
                                command, endpoint, mqtt_call_params):
    """Test successful drone command execution"""
    create_test_drone(drone_id="drone_1")
    mock_mqtt_client_instance.publish_command.return_value = True
    mock_mqtt_client_instance.wait_for_command_result.return_value = {
        "success": True,
        "message": f"{command} command executed successfully"
    }

    response = test_client.post(endpoint.format("drone_1"))
    data = RouteAssertions.assert_success(response)

    assert data["success"] is True

    # Check publish_command call - commands without params are called with 2 args, with params use 3 args
    if mqtt_call_params is None:
        mock_mqtt_client_instance.publish_command.assert_called_once_with("drone_1", command)
    else:
        mock_mqtt_client_instance.publish_command.assert_called_once_with("drone_1", command, mqtt_call_params)


@pytest.mark.parametrize("command,endpoint", [
    ("ARM", "/drones/{}/arm"),
    ("DISARM", "/drones/{}/disarm"),
    ("TAKEOFF", "/drones/{}/takeoff"),
    ("LAND", "/drones/{}/land"),
])
def test_drone_command_not_found(test_client, command, endpoint):
    """Test command on non-existent drone"""
    response = test_client.post(endpoint.format("nonexistent"))
    RouteAssertions.assert_not_found(response)


@pytest.mark.parametrize("mqtt_result,expected_status,assertion_method", [
    (False, 503, "assert_mqtt_unavailable"),  # MQTT unavailable
    (None, 504, "assert_timeout"),  # Command timeout
    ({"success": False, "message": "Cannot arm"}, 400, "assert_command_failed"),  # Command failed
])
def test_drone_command_error_conditions(test_client, create_test_drone, mock_mqtt_client_instance,
                                         mqtt_result, expected_status, assertion_method):
    """Test various error conditions for drone commands"""
    create_test_drone(drone_id="drone_1")

    if mqtt_result is False:
        mock_mqtt_client_instance.publish_command.return_value = False
    else:
        mock_mqtt_client_instance.publish_command.return_value = True
        mock_mqtt_client_instance.wait_for_command_result.return_value = mqtt_result

    response = test_client.post("/drones/drone_1/arm")

    assert response.status_code == expected_status
    assertion_func = getattr(RouteAssertions, assertion_method)
    assertion_func(response)


# ==================== Mission Tests ====================

def test_create_mission_success(test_client, create_test_drone):
    """Test successful mission creation"""
    create_test_drone(drone_id="drone_1")

    response = test_client.post(
        "/missions",
        json={
            "drone_id": "drone_1",
            "mission_type": "delivery",
            "waypoints": [
                {"lat": 43.6047, "lon": 1.4442, "alt": 10.0},
                {"lat": 43.6048, "lon": 1.4443, "alt": 10.0}
            ],
            "priority": 2
        }
    )

    data = RouteAssertions.assert_success(response)
    assert data["drone_id"] == "drone_1"
    assert data["mission_type"] == "delivery"
    assert data["status"] == "pending"
    assert data["priority"] == 2


def test_create_mission_drone_not_found(test_client):
    """Test creating mission for non-existent drone"""
    response = test_client.post(
        "/missions",
        json={
            "drone_id": "nonexistent",
            "mission_type": "delivery",
            "waypoints": [{"lat": 43.6047, "lon": 1.4442, "alt": 10.0}],
            "priority": 1
        }
    )

    assert response.status_code == 404
    assert "drone not found" in response.json()["detail"].lower()


def test_list_missions_multiple(test_client, create_test_drone, create_test_mission):
    """Test listing multiple missions"""
    create_test_drone(drone_id="drone_1")
    create_test_drone(drone_id="drone_2")
    create_test_mission(drone_id="drone_1", mission_type="delivery")
    create_test_mission(drone_id="drone_2", mission_type="surveillance")

    response = test_client.get("/missions")
    data = RouteAssertions.assert_success(response)

    assert len(data) == 2


@pytest.mark.parametrize("filter_by,filter_value,expected_count", [
    ("drone_id", "drone_1", 2),
    ("status", "in_progress", 1),
])
def test_list_missions_filtered(test_client, create_test_drone, create_test_mission,
                                filter_by, filter_value, expected_count):
    """Test listing missions with filters"""
    create_test_drone(drone_id="drone_1")
    create_test_drone(drone_id="drone_2")
    create_test_mission(drone_id="drone_1", mission_type="delivery", status="pending")
    create_test_mission(drone_id="drone_1", mission_type="patrol", status="in_progress")
    create_test_mission(drone_id="drone_2", mission_type="surveillance", status="completed")

    response = test_client.get(f"/missions?{filter_by}={filter_value}")
    data = RouteAssertions.assert_success(response)

    assert len(data) == expected_count
    if filter_by == "drone_id":
        assert all(m["drone_id"] == filter_value for m in data)
    elif filter_by == "status":
        assert all(m["status"] == filter_value for m in data)


@pytest.mark.parametrize("mission_exists", [True, False])
def test_get_mission(test_client, create_test_drone, create_test_mission, mission_exists):
    """Test getting specific mission by ID"""
    create_test_drone(drone_id="drone_1")
    mission = create_test_mission(drone_id="drone_1", mission_type="delivery") if mission_exists else None
    mission_id = mission.id if mission_exists else 9999

    response = test_client.get(f"/missions/{mission_id}")

    if not mission_exists:
        RouteAssertions.assert_not_found(response)
    else:
        data = RouteAssertions.assert_success(response)
        assert data["id"] == mission.id
        assert data["mission_type"] == "delivery"


@pytest.mark.parametrize("mission_exists", [True, False])
def test_update_mission_status(test_client, create_test_drone, create_test_mission, mission_exists):
    """Test updating mission status"""
    create_test_drone(drone_id="drone_1")
    mission = create_test_mission(drone_id="drone_1", status="pending") if mission_exists else None
    mission_id = mission.id if mission_exists else 9999

    response = test_client.put(f"/missions/{mission_id}/status?status=in_progress")

    if not mission_exists:
        RouteAssertions.assert_not_found(response)
    else:
        data = RouteAssertions.assert_success(response)
        assert "updated" in data["message"].lower()
