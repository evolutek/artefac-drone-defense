"""
CRUD operations for Warehouse model
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from ..models.warehouse import Warehouse
from ..models.inventory import Inventory


def get_warehouse(db: Session, warehouse_id: int) -> Optional[Warehouse]:
    return db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()


def get_warehouses(db: Session, skip: int = 0, limit: int = 100) -> List[Warehouse]:
    return db.query(Warehouse).offset(skip).limit(limit).all()


def create_warehouse(db: Session, name: str, latitude: float, longitude: float, address: Optional[str] = None, capacity: Optional[int] = None) -> Warehouse:
    w = Warehouse(name=name, latitude=latitude, longitude=longitude, address=address, capacity=capacity)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def update_warehouse(db: Session, warehouse_id: int, **fields) -> Optional[Warehouse]:
    w = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not w:
        return None
    for k, v in fields.items():
        try:
            if hasattr(w, k) and v is not None:
                setattr(w, k, v)
        except Exception:
            pass
    db.commit()
    db.refresh(w)
    return w


def delete_warehouse(db: Session, warehouse_id: int) -> bool:
    w = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not w:
        return False
    try:
        db.query(Inventory).filter(Inventory.warehouse_id == warehouse_id).delete()
    except Exception:
        pass
    db.delete(w)
    db.commit()
    return True
