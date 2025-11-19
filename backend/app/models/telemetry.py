"""
Telemetry database model for storing drone telemetry history
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from .database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    drone_id = Column(String, nullable=False, index=True)  # Reference to in-memory drone (no FK constraint)

    # Position
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)

    # Local position (relative to takeoff point)
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    position_z = Column(Float, nullable=True)

    # Velocity
    velocity_x = Column(Float, nullable=True)
    velocity_y = Column(Float, nullable=True)
    velocity_z = Column(Float, nullable=True)

    # Orientation (quaternion)
    orientation_x = Column(Float, nullable=True)
    orientation_y = Column(Float, nullable=True)
    orientation_z = Column(Float, nullable=True)
    orientation_w = Column(Float, nullable=True)

    # State
    battery_level = Column(Float, nullable=True)
    is_armed = Column(Boolean, default=False)
    flight_mode = Column(String, nullable=True)
    mavros_connected = Column(Boolean, default=False)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Telemetry(drone_id={self.drone_id}, timestamp={self.timestamp})>"
