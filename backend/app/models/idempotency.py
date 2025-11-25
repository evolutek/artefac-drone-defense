"""
Idempotency keys to deduplicate client commands across retries/fallbacks
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from .database import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(String, nullable=False)  # e.g., mission_status:42:completed
    key = Column(String, nullable=False)    # client-provided idempotency key
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('scope', 'key', name='uq_idempotency_scope_key'),
    )

