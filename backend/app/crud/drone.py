"""
CRUD operations for Drone model
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from ..models.drone import Drone


def get_drone(db: Session, drone_id: str) -> Optional[Drone]:
    """Get drone by drone_id"""
    return db.query(Drone).filter(Drone.drone_id == drone_id).first()


def get_drone_by_id(db: Session, id: int) -> Optional[Drone]:
    """Get drone by primary key id"""
    return db.query(Drone).filter(Drone.id == id).first()


def get_drones(db: Session, skip: int = 0, limit: int = 100) -> List[Drone]:
    """Get list of drones with pagination"""
    return db.query(Drone).offset(skip).limit(limit).all()


def create_drone(
    db: Session,
    drone_id: str,
    name: Optional[str] = None,
    model: str = "gz_x500",
) -> Drone:
    """Create new drone"""
    db_drone = Drone(
        drone_id=drone_id,
        name=name or drone_id,
        model=model,
        status="disconnected",
        created_at=datetime.utcnow(),
    )
    db.add(db_drone)
    db.commit()
    db.refresh(db_drone)
    return db_drone


def update_drone(
    db: Session,
    drone_id: str,
    **kwargs
) -> Optional[Drone]:
    """Update drone fields"""
    db_drone = get_drone(db, drone_id)
    if not db_drone:
        return None

    for key, value in kwargs.items():
        if hasattr(db_drone, key):
            setattr(db_drone, key, value)

    db_drone.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_drone)
    return db_drone


def update_drone_telemetry(
    db: Session,
    drone_id: str,
    position_x: Optional[float] = None,
    position_y: Optional[float] = None,
    position_z: Optional[float] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    altitude: Optional[float] = None,
    battery_level: Optional[float] = None,
    is_armed: Optional[bool] = None,
    flight_mode: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[Drone]:
    """Update drone with latest telemetry data"""
    update_data = {}

    if position_x is not None:
        update_data["position_x"] = position_x
    if position_y is not None:
        update_data["position_y"] = position_y
    if position_z is not None:
        update_data["position_z"] = position_z
    if latitude is not None:
        update_data["latitude"] = latitude
    if longitude is not None:
        update_data["longitude"] = longitude
    if altitude is not None:
        update_data["altitude"] = altitude
    if battery_level is not None:
        update_data["battery_level"] = battery_level
    if is_armed is not None:
        update_data["is_armed"] = is_armed
    if flight_mode is not None:
        update_data["flight_mode"] = flight_mode
    if status is not None:
        update_data["status"] = status

    update_data["last_heartbeat"] = datetime.utcnow()

    return update_drone(db, drone_id, **update_data)
