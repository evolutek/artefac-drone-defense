"""
CRUD operations for Mission model
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from ..models.mission import Mission


def get_mission(db: Session, mission_id: int) -> Optional[Mission]:
    """Get mission by id"""
    return db.query(Mission).filter(Mission.id == mission_id).first()


def get_missions(
    db: Session,
    drone_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Mission]:
    """Get list of missions with optional filters"""
    query = db.query(Mission)

    if drone_id:
        query = query.filter(Mission.drone_id == drone_id)
    if status:
        query = query.filter(Mission.status == status)

    return query.offset(skip).limit(limit).all()


def create_mission(
    db: Session,
    drone_id: str,
    mission_type: str,
    waypoints: Optional[str] = None,
    payload: Optional[str] = None,
    payloads: Optional[str] = None,
    note: Optional[str] = None,
    priority: int = 1,
) -> Mission:
    """Create new mission"""
    db_mission = Mission(
        drone_id=drone_id,
        mission_type=mission_type,
        waypoints=waypoints,
        payload=payload,
        payloads=payloads,
        note=note,
        priority=priority,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(db_mission)
    db.commit()
    db.refresh(db_mission)
    return db_mission


def delete_mission(
    db: Session,
    mission_id: int,
) -> Optional[Mission]:
    """Delete mission by id and return deleted record"""
    db_mission = get_mission(db, mission_id)
    if not db_mission:
        return None
    db.delete(db_mission)
    db.commit()
    return db_mission


def update_mission_status(
    db: Session,
    mission_id: int,
    status: str,
) -> Optional[Mission]:
    """Update mission status"""
    db_mission = get_mission(db, mission_id)
    if not db_mission:
        return None

    db_mission.status = status
    db_mission.updated_at = datetime.utcnow()

    if status == "in_progress" and not db_mission.started_at:
        db_mission.started_at = datetime.utcnow()
    elif status in ["completed", "failed"]:
        db_mission.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(db_mission)
    return db_mission


def update_mission_note(
    db: Session,
    mission_id: int,
    note: Optional[str],
) -> Optional[Mission]:
    """Update mission operator note"""
    db_mission = get_mission(db, mission_id)
    if not db_mission:
        return None

    db_mission.note = note
    db_mission.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_mission)
    return db_mission
