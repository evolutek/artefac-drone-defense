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
from .models import Drone, Mission, Telemetry
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
    logger.info("Starting application...")

    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Start MQTT client
    logger.info("Starting MQTT client...")
    mqtt_client.start()

    # Setup MQTT callbacks for WebSocket broadcasting
    from .websocket_manager import setup_mqtt_callbacks
    setup_mqtt_callbacks()

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
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    Returns status of backend, database, MQTT connection, and connected drones
    """
    # Check MQTT connection
    mqtt_status = mqtt_client.is_connected()

    # Count connected drones
    drones = crud.get_drones(db)
    connected_drones = len([d for d in drones if d.status == "connected"])

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "mqtt_connected": mqtt_status,
        "database": "operational",
        "drones_connected": connected_drones,
    }


# ==================== Drone Endpoints ====================

@app.post("/drones", response_model=DroneResponse)
def register_drone(drone: DroneCreate, db: Session = Depends(get_db)):
    """
    Register a new drone
    """
    # Check if drone already exists
    existing = crud.get_drone(db, drone.drone_id)
    if existing:
        raise HTTPException(status_code=400, detail="Drone already registered")

    db_drone = crud.create_drone(
        db,
        drone_id=drone.drone_id,
        name=drone.name,
        model=drone.model,
    )
    logger.info(f"Registered drone: {drone.drone_id}")
    return db_drone


@app.get("/drones", response_model=List[DroneResponse])
def list_drones(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List all registered drones
    """
    drones = crud.get_drones(db, skip=skip, limit=limit)
    return drones


@app.get("/drones/{drone_id}", response_model=DroneResponse)
def get_drone(drone_id: str, db: Session = Depends(get_db)):
    """
    Get drone details
    """
    drone = crud.get_drone(db, drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")
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
def arm_drone(drone_id: str, db: Session = Depends(get_db)):
    """
    Arm drone motors
    Publishes ARM command to MQTT
    """
    drone = crud.get_drone(db, drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

    # Publish ARM command via MQTT
    mqtt_client.publish_command(drone_id, "ARM")
    logger.info(f"ARM command sent to {drone_id}")

    return {"message": f"ARM command sent to {drone_id}"}


@app.post("/drones/{drone_id}/disarm")
def disarm_drone(drone_id: str, db: Session = Depends(get_db)):
    """
    Disarm drone motors
    Publishes DISARM command to MQTT
    """
    drone = crud.get_drone(db, drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

    # Publish DISARM command via MQTT
    mqtt_client.publish_command(drone_id, "DISARM")
    logger.info(f"DISARM command sent to {drone_id}")

    return {"message": f"DISARM command sent to {drone_id}"}


@app.post("/drones/{drone_id}/takeoff")
def takeoff_drone(drone_id: str, altitude: float = 5.0, db: Session = Depends(get_db)):
    """
    Command drone to takeoff
    Publishes TAKEOFF command to MQTT with altitude parameter
    """
    drone = crud.get_drone(db, drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

    # Publish TAKEOFF command via MQTT
    mqtt_client.publish_command(drone_id, "TAKEOFF", {"altitude": altitude})
    logger.info(f"TAKEOFF command sent to {drone_id} (altitude: {altitude}m)")

    return {"message": f"TAKEOFF command sent to {drone_id}", "altitude": altitude}


@app.post("/drones/{drone_id}/land")
def land_drone(drone_id: str, db: Session = Depends(get_db)):
    """
    Command drone to land
    Publishes LAND command to MQTT
    """
    drone = crud.get_drone(db, drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

    # Publish LAND command via MQTT
    mqtt_client.publish_command(drone_id, "LAND")
    logger.info(f"LAND command sent to {drone_id}")

    return {"message": f"LAND command sent to {drone_id}"}


# ==================== Mission Endpoints ====================

@app.post("/missions", response_model=MissionResponse)
def create_mission(mission: MissionCreate, db: Session = Depends(get_db)):
    """
    Create new mission
    """
    # Verify drone exists
    drone = crud.get_drone(db, mission.drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

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
