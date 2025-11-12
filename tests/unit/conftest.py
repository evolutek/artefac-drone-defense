"""
Shared pytest fixtures for unit tests
Provides reusable test fixtures for database, MQTT, and test data
"""
import pytest
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock, MagicMock
import json
from datetime import datetime

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set test environment variables
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MQTT_BROKER_HOST"] = "localhost"
os.environ["MQTT_BROKER_PORT"] = "1883"


# ==================== Database Fixtures ====================

@pytest.fixture(scope="function")
def db_engine():
    """
    Create an in-memory SQLite engine for testing with StaticPool.

    StaticPool ensures a single connection is reused across threads,
    making it safe to use check_same_thread=False with SQLite.
    This allows TestClient (which runs in a separate thread) to share
    the same database as test fixtures.

    isolation_level=None sets autocommit mode, ensuring all changes
    are immediately visible to all sessions sharing the connection.
    """
    from backend.app.models.database import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Single connection pool - thread-safe
        isolation_level=None,  # Autocommit mode for immediate visibility
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """
    Create a new database session for a test.
    Note: For tests using TestClient, data committed here will be visible
    to the TestClient because they share the same engine with StaticPool.
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()

    yield session

    session.rollback()
    session.close()


@pytest.fixture
def override_get_db(db_engine):
    """
    Override FastAPI's get_db dependency for testing.
    Creates a new session per request that shares the same engine.
    """
    def _override_get_db():
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
    return _override_get_db


# ==================== MQTT Fixtures ====================

@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client"""
    mock_client = MagicMock()
    mock_client.connect.return_value = 0
    mock_client.publish.return_value = MagicMock(rc=0)  # MQTT_ERR_SUCCESS
    mock_client.subscribe.return_value = (0, 1)
    mock_client.loop_start.return_value = None
    mock_client.loop_stop.return_value = None
    mock_client.disconnect.return_value = None
    return mock_client


@pytest.fixture
def mock_mqtt_client_instance(mock_mqtt_client, monkeypatch):
    """Mock the global mqtt_client instance"""
    from backend.app.mqtt_client import MQTTClient

    mock_instance = MQTTClient()
    mock_instance.client = mock_mqtt_client
    mock_instance.connected = True

    # Mock the publish_command method
    mock_instance.publish_command = Mock(return_value=True)

    # Mock the wait_for_command_result method
    mock_instance.wait_for_command_result = Mock(return_value={
        "success": True,
        "message": "Command executed successfully"
    })

    # Replace the global instance
    monkeypatch.setattr("backend.app.mqtt_client.mqtt_client", mock_instance)
    monkeypatch.setattr("backend.app.main.mqtt_client", mock_instance)

    return mock_instance


# ==================== WebSocket Fixtures ====================

@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection"""
    mock_ws = MagicMock()
    mock_ws.accept = MagicMock()
    mock_ws.send_text = MagicMock()
    mock_ws.send_json = MagicMock()
    mock_ws.receive_text = MagicMock(side_effect=Exception("Connection closed"))
    return mock_ws


# ==================== Enhanced MQTT Fixtures ====================

@pytest.fixture
def mqtt_command_success(mock_mqtt_client_instance):
    """Configure MQTT for successful command execution"""
    mock_mqtt_client_instance.publish_command.return_value = True
    mock_mqtt_client_instance.wait_for_command_result.return_value = {
        "success": True,
        "message": "Command executed successfully"
    }
    return mock_mqtt_client_instance


@pytest.fixture
def mqtt_command_timeout(mock_mqtt_client_instance):
    """Configure MQTT for command timeout"""
    mock_mqtt_client_instance.publish_command.return_value = True
    mock_mqtt_client_instance.wait_for_command_result.return_value = None
    return mock_mqtt_client_instance


@pytest.fixture
def mqtt_unavailable(mock_mqtt_client_instance):
    """Configure MQTT as unavailable"""
    mock_mqtt_client_instance.publish_command.return_value = False
    mock_mqtt_client_instance.is_connected = Mock(return_value=False)
    return mock_mqtt_client_instance


# ==================== Test Data Fixtures ====================

@pytest.fixture
def sample_drone_data():
    """Sample drone data for testing"""
    return {
        "drone_id": "drone_1",
        "name": "Test Drone 1",
        "model": "gz_x500",
        "status": "connected",
        "is_armed": False,
        "flight_mode": "MANUAL",
        "battery_level": 95.0,
        "position_x": 0.0,
        "position_y": 0.0,
        "position_z": 0.0,
    }


@pytest.fixture
def sample_telemetry_data():
    """Sample telemetry data for testing"""
    return {
        "drone_id": "drone_1",
        "position_x": 1.5,
        "position_y": 2.3,
        "position_z": 5.0,
        "velocity_x": 0.1,
        "velocity_y": 0.2,
        "velocity_z": 0.0,
        "orientation_x": 0.0,
        "orientation_y": 0.0,
        "orientation_z": 0.0,
        "orientation_w": 1.0,
        "battery_level": 89.5,
        "latitude": 43.6047,
        "longitude": 1.4442,
        "altitude": 5.0,
    }


@pytest.fixture
def sample_state_data():
    """Sample state data for testing"""
    return {
        "drone_id": "drone_1",
        "connected": True,
        "armed": False,
        "mode": "MANUAL",
    }


@pytest.fixture
def sample_command_result_data():
    """Sample command result data for testing"""
    return {
        "command": "ARM",
        "success": True,
        "message": "Drone armed successfully",
        "timestamp": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_mission_data():
    """Sample mission data for testing"""
    return {
        "drone_id": "drone_1",
        "mission_type": "delivery",
        "waypoints": [
            {"lat": 43.6047, "lon": 1.4442, "alt": 10.0},
            {"lat": 43.6048, "lon": 1.4443, "alt": 10.0},
        ],
        "priority": 1,
        "status": "pending",
    }


# ==================== Helper Functions ====================

@pytest.fixture
def create_test_drone(db_session, sample_drone_data):
    """Helper function to create a test drone in the database"""
    def _create_drone(**kwargs):
        from backend.app import crud

        # Merge provided kwargs with sample data
        drone_data = {**sample_drone_data, **kwargs}
        # crud.create_drone already commits, so no need to commit again
        drone = crud.create_drone(
            db_session,
            drone_id=drone_data["drone_id"],
            name=drone_data.get("name"),
            model=drone_data.get("model"),
        )

        # Update drone with additional properties if provided
        update_fields = {}
        if "status" in kwargs:
            update_fields["status"] = kwargs["status"]
        if "is_armed" in kwargs:
            update_fields["is_armed"] = kwargs["is_armed"]
        if "flight_mode" in kwargs:
            update_fields["flight_mode"] = kwargs["flight_mode"]
        if "battery_level" in kwargs:
            update_fields["battery_level"] = kwargs["battery_level"]

        if update_fields:
            drone = crud.update_drone(
                db_session,
                drone_id=drone_data["drone_id"],
                **update_fields
            )

        return drone

    return _create_drone


@pytest.fixture
def create_test_telemetry(db_session, sample_telemetry_data):
    """Helper function to create test telemetry in the database"""
    def _create_telemetry(drone_id=None, **kwargs):
        from backend.app import crud

        # Merge provided kwargs with sample data
        telemetry_data = {**sample_telemetry_data, **kwargs}
        if drone_id:
            telemetry_data["drone_id"] = drone_id

        # crud.create_telemetry already commits, so no need to commit again
        telemetry = crud.create_telemetry(db_session, **telemetry_data)
        return telemetry

    return _create_telemetry


@pytest.fixture
def create_test_mission(db_session, sample_mission_data):
    """Helper function to create a test mission in the database"""
    def _create_mission(drone_id=None, **kwargs):
        from backend.app import crud

        # Merge provided kwargs with sample data
        mission_data = {**sample_mission_data, **kwargs}
        if drone_id:
            mission_data["drone_id"] = drone_id

        # Convert waypoints to JSON string
        waypoints_json = json.dumps(mission_data["waypoints"])

        # crud.create_mission already commits, so no need to commit again
        mission = crud.create_mission(
            db_session,
            drone_id=mission_data["drone_id"],
            mission_type=mission_data["mission_type"],
            waypoints=waypoints_json,
            priority=mission_data.get("priority", 1),
        )

        # Update status if different from pending (default)
        if mission_data.get("status") and mission_data["status"] != "pending":
            mission = crud.update_mission_status(
                db_session,
                mission_id=mission.id,
                status=mission_data["status"],
            )

        return mission

    return _create_mission


# ==================== FastAPI Fixtures ====================

@pytest.fixture
def test_client(override_get_db, mock_mqtt_client_instance):
    """Create a FastAPI TestClient with mocked dependencies"""
    from fastapi.testclient import TestClient
    from backend.app.main import app, get_db

    # Override the get_db dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create test client without lifespan (no MQTT/DB initialization)
    with TestClient(app) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()
