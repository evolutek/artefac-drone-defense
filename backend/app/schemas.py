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
    id: int
    drone_id: str
    name: Optional[str]
    model: str
    status: str
    battery_level: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]
    altitude: Optional[float]
    position_x: Optional[float]
    position_y: Optional[float]
    position_z: Optional[float]
    is_armed: bool
    flight_mode: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_heartbeat: Optional[datetime]

    class Config:
        from_attributes = True


# ==================== Mission Schemas ====================

class MissionCreate(BaseModel):
    drone_id: str = Field(..., description="Drone ID assigned to this mission")
    mission_type: str = Field(..., description="Type: delivery, surveillance, patrol")
    waypoints: Optional[List[dict]] = Field(None, description="List of waypoint coordinates")
    priority: int = Field(default=1, description="Priority level (1=low, 2=medium, 3=high)")
    payload: Optional[dict] = Field(None, description="Commande unique: {item_name, weight_kg, quantity}")
    payloads: Optional[List[dict]] = Field(None, description="Lignes de commande: liste d'objets")
    note: Optional[str] = Field(None, description="Note opérateur")


class MissionResponse(BaseModel):
    id: int
    drone_id: str
    mission_type: str
    status: str
    priority: int
    waypoints: Optional[str]  # JSON string
    payload: Optional[str]  # JSON string
    payloads: Optional[str]  # JSON string
    note: Optional[str]
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


# ==================== Weather Schemas ====================

class WeatherCheckRequest(BaseModel):
    lat: float = Field(..., description="Latitude du point de mission")
    lon: float = Field(..., description="Longitude du point de mission")


class WeatherMetricsResponse(BaseModel):
    wind_speed: Optional[float] = Field(None, description="Vitesse du vent (m/s)")
    wind_gusts: Optional[float] = Field(None, description="Rafales (m/s)")
    precipitation: Optional[float] = Field(None, description="Précipitations (mm/h)")
    temperature: Optional[float] = Field(None, description="Température (°C)")
    timestamp: datetime = Field(..., description="Timestamp UTC des mesures")


class WeatherCheckResponse(BaseModel):
    risk: str = Field(..., description="Niveau de risque: safe | caution | blocked")
    reason: str = Field(..., description="Motif synthétique de l'évaluation")
    metrics: WeatherMetricsResponse


# ==================== Warehouse & Product Schemas ====================

class WarehouseCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    capacity: Optional[int] = None


class WarehouseResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    address: Optional[str]
    capacity: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    category: Optional[str] = ""
    weight_kg: Optional[float] = None
    image_url: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    weight_kg: Optional[float]
    image_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryEntry(BaseModel):
    product_id: int
    quantity: int


# ==================== Delivery Estimation ====================

class DeliveryEstimateRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    payload_weight_kg: float = Field(default=1.0)
    drone_id: Optional[str] = None


class DeliveryEstimateResponse(BaseModel):
    distance_m: float
    eta_minutes: Optional[float]
    risk: str
    reason: str
    recommended_speed_mps: Optional[float]
    required_autonomy_minutes: Optional[float]
