"""
Drone Mission API - Backend
FastAPI application for drone fleet management
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from .models.database import init_db, get_db
from .models import Mission, Telemetry
from . import crud
from .schemas import (
    DroneCreate,
    DroneResponse,
    MissionCreate,
    MissionResponse,
    TelemetryResponse,
    HealthResponse,
)
from .mqtt_client import mqtt_client
from .websocket_manager import websocket_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Initialize database and MQTT client on startup
    """
    import asyncio

    logger.info("Starting application...")

    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Start MQTT client
    logger.info("Starting MQTT client...")
    mqtt_client.start()

    # Setup MQTT callbacks for WebSocket broadcasting with the main event loop
    from .websocket_manager import setup_mqtt_callbacks
    event_loop = asyncio.get_event_loop()
    setup_mqtt_callbacks(event_loop)

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application...")
    mqtt_client.stop()


app = FastAPI(
    title="Drone Mission API",
    description="Backend for drone fleet management and mission planning",
    version="1.0.0-mvp",
    lifespan=lifespan,
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health Check ====================

@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint
    Returns status of backend, MQTT connection, and active drones
    """
    from .drone_state_manager import drone_state_manager

    # Check MQTT connection
    mqtt_status = mqtt_client.is_connected()

    # Count active drones from in-memory state manager
    active_drones = drone_state_manager.get_active_drones(timeout_seconds=30)
    connected_drones = len(active_drones)

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "mqtt_connected": mqtt_status,
        "database": "operational",  # Keep for compatibility, but missions/telemetry still in DB
        "drones_connected": connected_drones,
    }


# ==================== Drone Endpoints ====================
# Note: Drone registration is automatic via MQTT telemetry
# No POST /drones endpoint needed - drones auto-register when they start publishing

@app.get("/drones", response_model=List[DroneResponse])
def list_drones(
    skip: int = 0,
    limit: int = 100,
    only_active: bool = True,
    timeout_seconds: int = 30
):
    """
    List drones from in-memory state manager

    Args:
        skip: Pagination offset (not used with in-memory state)
        limit: Maximum number of results
        only_active: If True, only return drones with recent heartbeat (default: True)
        timeout_seconds: Heartbeat timeout in seconds (default: 30)
    """
    from .drone_state_manager import drone_state_manager

    if only_active:
        drones_dict = drone_state_manager.get_active_drones(timeout_seconds=timeout_seconds)
    else:
        drones_dict = drone_state_manager.get_all_drones()

    # Convert dict to list and apply limit
    drones_list = list(drones_dict.values())

    # Apply pagination (skip not really useful with in-memory, but keep for API compatibility)
    if skip > 0:
        drones_list = drones_list[skip:]
    if limit > 0:
        drones_list = drones_list[:limit]

    return drones_list


@app.get("/drones/{drone_id}", response_model=DroneResponse)
def get_drone(drone_id: str):
    """
    Get drone details from in-memory state manager
    """
    from .drone_state_manager import drone_state_manager

    drone = drone_state_manager.get_drone(drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found or inactive")
    return drone


@app.get("/drones/{drone_id}/telemetry", response_model=TelemetryResponse)
def get_drone_telemetry(drone_id: str, db: Session = Depends(get_db)):
    """
    Get latest telemetry for a drone
    """
    telemetry = crud.get_latest_telemetry(db, drone_id)
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry data available")
    return telemetry


@app.post("/drones/{drone_id}/arm")
def arm_drone(drone_id: str):
    """
    Arm drone motors
    Publishes ARM command to MQTT and waits for result
    No DB check needed - if drone publishes on MQTT, it exists
    """
    # Publish ARM command via MQTT
    success = mqtt_client.publish_command(drone_id, "ARM")
    if not success:
        raise HTTPException(status_code=503, detail="MQTT broker not available")

    logger.info(f"ARM command sent to {drone_id}, waiting for result...")

    # Wait for command result from ROS2 bridge
    result = mqtt_client.wait_for_command_result(drone_id, "ARM", timeout=5.0)

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Timeout waiting for drone response - check if ROS2 bridge is running"
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "ARM command failed")
        )

    return {
        "success": True,
        "message": result.get("message", "Drone armed successfully")
    }


@app.post("/drones/{drone_id}/disarm")
def disarm_drone(drone_id: str):
    """
    Disarm drone motors
    Publishes DISARM command to MQTT and waits for result
    No DB check needed - if drone publishes on MQTT, it exists
    """
    # Publish DISARM command via MQTT
    success = mqtt_client.publish_command(drone_id, "DISARM")
    if not success:
        raise HTTPException(status_code=503, detail="MQTT broker not available")

    logger.info(f"DISARM command sent to {drone_id}, waiting for result...")

    # Wait for command result from ROS2 bridge
    result = mqtt_client.wait_for_command_result(drone_id, "DISARM", timeout=5.0)

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Timeout waiting for drone response - check if ROS2 bridge is running"
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "DISARM command failed")
        )

    return {
        "success": True,
        "message": result.get("message", "Drone disarmed successfully")
    }


@app.post("/drones/{drone_id}/takeoff")
def takeoff_drone(drone_id: str, altitude: float = 5.0):
    """
    Command drone to takeoff
    Publishes TAKEOFF command to MQTT with altitude parameter and waits for result
    No DB check needed - if drone publishes on MQTT, it exists
    """
    # Publish TAKEOFF command via MQTT
    success = mqtt_client.publish_command(drone_id, "TAKEOFF", {"altitude": altitude})
    if not success:
        raise HTTPException(status_code=503, detail="MQTT broker not available")

    logger.info(f"TAKEOFF command sent to {drone_id} (altitude: {altitude}m), waiting for result...")

    # Wait for command result from ROS2 bridge
    result = mqtt_client.wait_for_command_result(drone_id, "TAKEOFF", timeout=5.0)

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Timeout waiting for drone response - check if ROS2 bridge is running"
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "TAKEOFF command failed")
        )

    return {
        "success": True,
        "message": result.get("message", "Takeoff command sent successfully"),
        "altitude": altitude
    }


@app.post("/drones/{drone_id}/land")
def land_drone(drone_id: str):
    """
    Command drone to land
    Publishes LAND command to MQTT and waits for result
    No DB check needed - if drone publishes on MQTT, it exists
    """
    # Publish LAND command via MQTT
    success = mqtt_client.publish_command(drone_id, "LAND")
    if not success:
        raise HTTPException(status_code=503, detail="MQTT broker not available")

    logger.info(f"LAND command sent to {drone_id}, waiting for result...")

    # Wait for command result from ROS2 bridge
    result = mqtt_client.wait_for_command_result(drone_id, "LAND", timeout=5.0)

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Timeout waiting for drone response - check if ROS2 bridge is running"
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "LAND command failed")
        )

    return {
        "success": True,
        "message": result.get("message", "Land command sent successfully")
    }


# ==================== Mission Endpoints ====================

@app.post("/missions", response_model=MissionResponse)
def create_mission(mission: MissionCreate, db: Session = Depends(get_db)):
    """
    Create new mission
    """
    # Verify drone exists in state manager
    from .drone_state_manager import drone_state_manager
    drone = drone_state_manager.get_drone(mission.drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found or inactive")

    # Convert waypoints to JSON string if needed
    import json
    waypoints_json = json.dumps(mission.waypoints) if mission.waypoints else None

    db_mission = crud.create_mission(
        db,
        drone_id=mission.drone_id,
        mission_type=mission.mission_type,
        waypoints=waypoints_json,
        priority=mission.priority,
    )
    logger.info(f"Created mission {db_mission.id} for drone {mission.drone_id}")

    return db_mission


@app.get("/missions", response_model=List[MissionResponse])
def list_missions(
    drone_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List missions with optional filters
    """
    missions = crud.get_missions(db, drone_id=drone_id, status=status, skip=skip, limit=limit)
    return missions


@app.get("/missions/{mission_id}", response_model=MissionResponse)
def get_mission(mission_id: int, db: Session = Depends(get_db)):
    """
    Get mission details
    """
    mission = crud.get_mission(db, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@app.put("/missions/{mission_id}/status")
def update_mission_status(mission_id: int, status: str, db: Session = Depends(get_db)):
    """
    Update mission status
    """
    mission = crud.update_mission_status(db, mission_id, status)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    logger.info(f"Mission {mission_id} status updated to {status}")
    return {"message": f"Mission {mission_id} status updated to {status}"}


# ==================== WebSocket Endpoints ====================

@app.websocket("/ws/telemetry")
async def websocket_telemetry_all(websocket: WebSocket):
    """
    WebSocket endpoint for real-time telemetry from all drones
    """
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and wait for disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


@app.websocket("/ws/drone/{drone_id}")
async def websocket_telemetry_drone(websocket: WebSocket, drone_id: str):
    """
    WebSocket endpoint for real-time telemetry from specific drone
    """
    await websocket_manager.connect(websocket, drone_id)
    try:
        while True:
            # Keep connection alive and wait for disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, drone_id)
