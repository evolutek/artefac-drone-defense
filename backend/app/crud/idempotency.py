from sqlalchemy.orm import Session
from ..models.idempotency import IdempotencyKey


def has_key(db: Session, scope: str, key: str) -> bool:
    return db.query(IdempotencyKey).filter(IdempotencyKey.scope == scope, IdempotencyKey.key == key).first() is not None


def record_key(db: Session, scope: str, key: str) -> None:
    rec = IdempotencyKey(scope=scope, key=key)
    db.add(rec)
    db.commit()
