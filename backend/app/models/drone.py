"""
Drone database model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from .database import Base


class Drone(Base):
    __tablename__ = "drones"

    id = Column(Integer, primary_key=True, index=True)
    drone_id = Column(String, unique=True, index=True, nullable=False)  # e.g., "drone_1"
    name = Column(String, nullable=True)
    model = Column(String, default="gz_x500")
    status = Column(String, default="disconnected")  # disconnected, connected, armed, flying
    battery_level = Column(Float, nullable=True)

    # Position
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)

    # Local position (relative to takeoff point)
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    position_z = Column(Float, nullable=True)

    # State
    is_armed = Column(Boolean, default=False)
    flight_mode = Column(String, nullable=True)  # e.g., "MANUAL", "OFFBOARD", "AUTO.MISSION"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_heartbeat = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Drone(drone_id={self.drone_id}, status={self.status}, armed={self.is_armed})>"
