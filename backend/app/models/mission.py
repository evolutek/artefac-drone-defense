"""
Mission database model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    drone_id = Column(String, ForeignKey("drones.drone_id"), nullable=False)
    mission_type = Column(String, nullable=False)  # delivery, surveillance, patrol
    status = Column(String, default="pending")  # pending, assigned, in_progress, completed, failed
    priority = Column(Integer, default=1)  # 1=low, 2=medium, 3=high

    # Waypoints stored as JSON text
    waypoints = Column(Text, nullable=True)  # JSON array of {lat, lon, alt}

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Mission(id={self.id}, type={self.mission_type}, status={self.status})>"
