"""
Product database model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from .database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    weight_kg = Column(Float, nullable=True)
    image_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Product(name={self.name}, weight={self.weight_kg})>"

