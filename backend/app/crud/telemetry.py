"""
CRUD operations for Telemetry model
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models.telemetry import Telemetry


def create_telemetry(
    db: Session,
    drone_id: str,
    **kwargs
) -> Telemetry:
    """Create new telemetry entry"""
    db_telemetry = Telemetry(
        drone_id=drone_id,
        timestamp=datetime.utcnow(),
        **kwargs
    )
    db.add(db_telemetry)
    db.commit()
    db.refresh(db_telemetry)
    return db_telemetry


def get_latest_telemetry(db: Session, drone_id: str) -> Optional[Telemetry]:
    """Get latest telemetry entry for a drone"""
    return (
        db.query(Telemetry)
        .filter(Telemetry.drone_id == drone_id)
        .order_by(desc(Telemetry.timestamp))
        .first()
    )


def get_telemetry_history(
    db: Session,
    drone_id: str,
    hours: int = 24,
    limit: int = 1000,
) -> List[Telemetry]:
    """Get telemetry history for a drone"""
    since = datetime.utcnow() - timedelta(hours=hours)
    return (
        db.query(Telemetry)
        .filter(Telemetry.drone_id == drone_id)
        .filter(Telemetry.timestamp >= since)
        .order_by(desc(Telemetry.timestamp))
        .limit(limit)
        .all()
    )
