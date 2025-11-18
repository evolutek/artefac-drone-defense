"""
Unit tests for CRUD operations
Tests database operations for Drone, Telemetry, and Mission models
"""
import pytest
from datetime import datetime, timedelta
import json
from backend.app import crud


# ==================== Shared Test Helpers ====================

class CRUDAssertions:
    """Shared assertion helpers for CRUD tests"""

    @staticmethod
    def assert_not_found(result):
        """Assert that a CRUD operation returned None (not found)"""
        assert result is None

    @staticmethod
    def assert_drone_fields(drone, drone_id, name=None, model="gz_x500", status="disconnected"):
        """Assert common drone fields"""
        assert drone.drone_id == drone_id
        assert drone.name == (name or drone_id)
        assert drone.model == model
        assert drone.status == status
        assert drone.created_at is not None


# ==================== Drone CRUD Tests ====================

def test_create_drone(db_session):
    """Test creating a new drone with all parameters"""
    drone = crud.create_drone(
        db_session,
        drone_id="drone_test",
        name="Test Drone",
        model="gz_x500"
    )

    CRUDAssertions.assert_drone_fields(drone, "drone_test", "Test Drone", "gz_x500")
    assert drone.id is not None
    assert drone.is_armed is False


@pytest.mark.parametrize("operation,drone_id,expected_result", [
    ("get", "drone_1", "found"),
    ("get", "nonexistent", "not_found"),
    ("get_by_id", 1, "found"),
])
def test_get_drone_operations(db_session, create_test_drone, operation, drone_id, expected_result):
    """Test various drone retrieval operations"""
    # Setup
    created_drone = create_test_drone(drone_id="drone_1", name="Test")

    # Act
    if operation == "get":
        result = crud.get_drone(db_session, drone_id)
    elif operation == "get_by_id":
        result = crud.get_drone_by_id(db_session, created_drone.id if expected_result == "found" else 9999)

    # Assert
    if expected_result == "not_found":
        CRUDAssertions.assert_not_found(result)
    else:
        assert result is not None
        assert result.drone_id == "drone_1"


def test_get_drones_multiple(db_session, create_test_drone):
    """Test getting multiple drones"""
    create_test_drone(drone_id="drone_1")
    create_test_drone(drone_id="drone_2")
    create_test_drone(drone_id="drone_3")

    drones = crud.get_drones(db_session)
    assert len(drones) == 3


def test_get_drones_pagination(db_session, create_test_drone):
    """Test drone pagination"""
    for i in range(1, 6):
        create_test_drone(drone_id=f"drone_{i}")

    drones = crud.get_drones(db_session, skip=2, limit=2)
    assert len(drones) == 2
    assert drones[0].drone_id == "drone_3"
    assert drones[1].drone_id == "drone_4"


@pytest.mark.parametrize("update_fields,expected_values", [
    ({"status": "connected", "flight_mode": "MANUAL", "battery_level": 95.5},
     {"status": "connected", "flight_mode": "MANUAL", "battery_level": 95.5}),
    ({"status": "armed"},
     {"status": "armed"}),
])
def test_update_drone(db_session, create_test_drone, update_fields, expected_values):
    """Test updating drone fields"""
    create_test_drone(drone_id="drone_1", status="disconnected")

    updated_drone = crud.update_drone(db_session, "drone_1", **update_fields)

    assert updated_drone is not None
    for field, expected_value in expected_values.items():
        assert getattr(updated_drone, field) == expected_value
    assert updated_drone.updated_at is not None


def test_update_drone_not_found(db_session):
    """Test updating non-existent drone"""
    result = crud.update_drone(db_session, "nonexistent", status="armed")
    CRUDAssertions.assert_not_found(result)


@pytest.mark.parametrize("telemetry_data", [
    {"position_x": 1.5, "position_y": 2.3, "position_z": 5.0, "battery_level": 85.5,
     "latitude": 43.6047, "longitude": 1.4442, "altitude": 5.0},
    {"position_x": 5.0, "battery_level": 90.0},  # Partial update
])
def test_update_drone_telemetry(db_session, create_test_drone, telemetry_data):
    """Test updating drone with telemetry data"""
    create_test_drone(drone_id="drone_1")

    updated_drone = crud.update_drone_telemetry(db_session, "drone_1", **telemetry_data)

    assert updated_drone is not None
    for field, expected_value in telemetry_data.items():
        assert getattr(updated_drone, field) == expected_value
    assert updated_drone.last_heartbeat is not None


# ==================== Telemetry CRUD Tests ====================

def test_create_telemetry(db_session, create_test_drone):
    """Test creating telemetry entry"""
    create_test_drone(drone_id="drone_1")

    telemetry = crud.create_telemetry(
        db_session,
        drone_id="drone_1",
        position_x=1.5,
        position_y=2.3,
        position_z=5.0,
        velocity_x=0.1,
        velocity_y=0.2,
        velocity_z=0.0,
        battery_level=85.5
    )

    assert telemetry.id is not None
    assert telemetry.drone_id == "drone_1"
    assert telemetry.position_x == 1.5
    assert telemetry.battery_level == 85.5
    assert telemetry.timestamp is not None


def test_get_latest_telemetry(db_session, create_test_drone, create_test_telemetry):
    """Test getting latest telemetry entry"""
    create_test_drone(drone_id="drone_1")
    create_test_telemetry(drone_id="drone_1", battery_level=90.0)
    create_test_telemetry(drone_id="drone_1", battery_level=85.0)
    latest = create_test_telemetry(drone_id="drone_1", battery_level=80.0)

    telemetry = crud.get_latest_telemetry(db_session, "drone_1")

    assert telemetry is not None
    assert telemetry.id == latest.id
    assert telemetry.battery_level == 80.0


def test_get_telemetry_history(db_session, create_test_drone):
    """Test getting telemetry history"""
    create_test_drone(drone_id="drone_1")

    # Create 5 telemetry entries
    for i in range(5):
        crud.create_telemetry(
            db_session,
            drone_id="drone_1",
            position_z=float(i),
            battery_level=100.0 - i
        )

    history = crud.get_telemetry_history(db_session, "drone_1", hours=24)

    assert len(history) == 5
    # Should be in descending order (most recent first)
    assert history[0].battery_level == 96.0
    assert history[4].battery_level == 100.0


def test_get_telemetry_history_limit(db_session, create_test_drone):
    """Test telemetry history with limit"""
    create_test_drone(drone_id="drone_1")

    for i in range(10):
        crud.create_telemetry(db_session, drone_id="drone_1", battery_level=float(i))

    history = crud.get_telemetry_history(db_session, "drone_1", hours=24, limit=5)
    assert len(history) == 5


def test_get_telemetry_history_time_filter(db_session, create_test_drone):
    """Test telemetry history with time filter"""
    from backend.app.models.telemetry import Telemetry

    create_test_drone(drone_id="drone_1")

    # Create old entry (25 hours ago)
    old_entry = Telemetry(
        drone_id="drone_1",
        battery_level=50.0,
        timestamp=datetime.utcnow() - timedelta(hours=25)
    )
    db_session.add(old_entry)
    db_session.commit()

    # Create recent entry
    crud.create_telemetry(db_session, drone_id="drone_1", battery_level=90.0)

    history = crud.get_telemetry_history(db_session, "drone_1", hours=24)

    # Should only get recent entry
    assert len(history) == 1
    assert history[0].battery_level == 90.0


# ==================== Mission CRUD Tests ====================

def test_create_mission(db_session, create_test_drone):
    """Test creating a new mission"""
    create_test_drone(drone_id="drone_1")

    waypoints_json = json.dumps([
        {"lat": 43.6047, "lon": 1.4442, "alt": 10.0},
        {"lat": 43.6048, "lon": 1.4443, "alt": 10.0}
    ])

    mission = crud.create_mission(
        db_session,
        drone_id="drone_1",
        mission_type="delivery",
        waypoints=waypoints_json,
        priority=2
    )

    assert mission.id is not None
    assert mission.drone_id == "drone_1"
    assert mission.mission_type == "delivery"
    assert mission.status == "pending"
    assert mission.priority == 2
    assert mission.waypoints is not None
    assert mission.created_at is not None


@pytest.mark.parametrize("mission_id,expected_result", [
    (1, "found"),
    (9999, "not_found"),
])
def test_get_mission(db_session, create_test_drone, create_test_mission, mission_id, expected_result):
    """Test getting mission by ID"""
    create_test_drone(drone_id="drone_1")
    created_mission = create_test_mission(drone_id="drone_1")

    if expected_result == "found":
        mission_id = created_mission.id

    mission = crud.get_mission(db_session, mission_id)

    if expected_result == "not_found":
        CRUDAssertions.assert_not_found(mission)
    else:
        assert mission is not None
        assert mission.id == created_mission.id
        assert mission.drone_id == "drone_1"


def test_get_missions_multiple(db_session, create_test_drone, create_test_mission):
    """Test getting multiple missions"""
    create_test_drone(drone_id="drone_1")
    create_test_mission(drone_id="drone_1", mission_type="delivery")
    create_test_mission(drone_id="drone_1", mission_type="patrol")

    missions = crud.get_missions(db_session)
    assert len(missions) == 2


@pytest.mark.parametrize("filter_by,filter_value,expected_count", [
    ("drone_id", "drone_1", 2),
    ("status", "in_progress", 1),
])
def test_get_missions_filtered(db_session, create_test_drone, create_test_mission, filter_by, filter_value, expected_count):
    """Test filtering missions by drone_id or status"""
    create_test_drone(drone_id="drone_1")
    create_test_drone(drone_id="drone_2")
    create_test_mission(drone_id="drone_1", mission_type="delivery", status="pending")
    create_test_mission(drone_id="drone_1", mission_type="patrol", status="in_progress")
    create_test_mission(drone_id="drone_2", mission_type="surveillance", status="completed")

    filter_kwargs = {filter_by: filter_value}
    missions = crud.get_missions(db_session, **filter_kwargs)

    assert len(missions) == expected_count


def test_get_missions_pagination(db_session, create_test_drone, create_test_mission):
    """Test mission pagination"""
    create_test_drone(drone_id="drone_1")
    for i in range(5):
        create_test_mission(drone_id="drone_1")

    missions = crud.get_missions(db_session, skip=2, limit=2)
    assert len(missions) == 2


@pytest.mark.parametrize("status,sets_started_at,sets_completed_at", [
    ("in_progress", True, False),
    ("completed", False, True),
    ("failed", False, True),
])
def test_update_mission_status(db_session, create_test_drone, create_test_mission, status, sets_started_at, sets_completed_at):
    """Test updating mission status with timestamp logic"""
    create_test_drone(drone_id="drone_1")
    mission = create_test_mission(drone_id="drone_1", status="pending")

    updated_mission = crud.update_mission_status(db_session, mission.id, status)

    assert updated_mission is not None
    assert updated_mission.status == status
    assert updated_mission.updated_at is not None

    if sets_started_at:
        assert updated_mission.started_at is not None
    if sets_completed_at:
        assert updated_mission.completed_at is not None


def test_update_mission_status_not_found(db_session):
    """Test updating status of non-existent mission"""
    result = crud.update_mission_status(db_session, 9999, "completed")
    CRUDAssertions.assert_not_found(result)


def test_update_mission_status_idempotent(db_session, create_test_drone, create_test_mission):
    """Test updating mission status multiple times doesn't override started_at"""
    create_test_drone(drone_id="drone_1")
    mission = create_test_mission(drone_id="drone_1", status="pending")

    # Update to in_progress twice
    first_update = crud.update_mission_status(db_session, mission.id, "in_progress")
    first_started_at = first_update.started_at

    second_update = crud.update_mission_status(db_session, mission.id, "in_progress")

    # started_at should not change on second update
    assert second_update.started_at == first_started_at
