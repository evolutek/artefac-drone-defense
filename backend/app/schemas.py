"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== Drone Schemas ====================

class DroneCreate(BaseModel):
    drone_id: str = Field(..., description="Unique drone identifier (e.g., 'drone_1')")
    name: Optional[str] = Field(None, description="Human-readable drone name")
    model: str = Field(default="gz_x500", description="Drone model")


class DroneResponse(BaseModel):
    drone_id: str
    status: str = "connected"
    battery_level: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    position_z: Optional[float] = None
    velocity_x: Optional[float] = None
    velocity_y: Optional[float] = None
    velocity_z: Optional[float] = None
    orientation_x: Optional[float] = None
    orientation_y: Optional[float] = None
    orientation_z: Optional[float] = None
    orientation_w: Optional[float] = None
    is_armed: bool = False
    flight_mode: Optional[str] = None
    mavros_connected: Optional[bool] = None
    last_update: Optional[datetime] = None
    created_at: Optional[datetime] = None  # Kept for backward compatibility

    class Config:
        from_attributes = False  # Data comes from dict, not SQLAlchemy model


# ==================== Zone Schemas ====================

class ZoneResponse(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    zone_model_name: Optional[str] = None
    type: str  # jamming, no-fly, restricted
    position: Optional[dict] = None  # {x, y, z}
    radius: Optional[float] = None
    status: str = "connected"
    spawned_at: Optional[str] = None  # ISO format string
    last_update: Optional[datetime] = None

    class Config:
        from_attributes = False


# ==================== Warehouse Schemas ====================

class WarehouseResponse(BaseModel):
    entrepot_id: str
    entrepot_name: Optional[str] = None
    entrepot_model_name: Optional[str] = None
    entrepot_type: Optional[str] = None  # medicaments, foods, ammo, equipements
    position: Optional[dict] = None  # {x, y, z}
    status: str = "connected"
    spawned_at: Optional[str] = None  # ISO format string
    last_update: Optional[datetime] = None

    class Config:
        from_attributes = False


# ==================== Delivery Schemas ====================

class DeliveryResponse(BaseModel):
    livraison_id: str
    livraison_name: Optional[str] = None
    type: Optional[str] = None  # medicaments, foods, ammo, equipements
    position: Optional[dict] = None  # {x, y, z}
    status: str = "connected"
    spawned_at: Optional[str] = None  # ISO format string
    last_update: Optional[datetime] = None

    class Config:
        from_attributes = False


# ==================== Mission Schemas ====================

class MissionCreate(BaseModel):
    drone_id: str = Field(..., description="Drone ID assigned to this mission")
    mission_type: str = Field(..., description="Type: delivery, surveillance, patrol")
    waypoints: Optional[List[dict]] = Field(None, description="List of waypoint coordinates")
    priority: int = Field(default=1, description="Priority level (1=low, 2=medium, 3=high)")


class MissionResponse(BaseModel):
    id: int
    drone_id: str
    mission_type: str
    status: str
    priority: int
    waypoints: Optional[str]  # JSON string
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ==================== Telemetry Schemas ====================

class TelemetryResponse(BaseModel):
    id: int
    drone_id: str
    latitude: Optional[float]
    longitude: Optional[float]
    altitude: Optional[float]
    position_x: Optional[float]
    position_y: Optional[float]
    position_z: Optional[float]
    velocity_x: Optional[float]
    velocity_y: Optional[float]
    velocity_z: Optional[float]
    orientation_x: Optional[float]
    orientation_y: Optional[float]
    orientation_z: Optional[float]
    orientation_w: Optional[float]
    battery_level: Optional[float]
    is_armed: bool
    flight_mode: Optional[str]
    mavros_connected: bool
    timestamp: datetime

    class Config:
        from_attributes = True


# ==================== Health Check Schema ====================

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    mqtt_connected: bool
    database: str
    drones_connected: int
