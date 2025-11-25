"""
CRUD operations for Inventory model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.inventory import Inventory


def get_inventory_for_warehouse(db: Session, warehouse_id: int) -> List[Inventory]:
    return db.query(Inventory).filter(Inventory.warehouse_id == warehouse_id).all()


def upsert_inventory(db: Session, warehouse_id: int, product_id: int, quantity: int) -> Inventory:
    item = db.query(Inventory).filter(Inventory.warehouse_id == warehouse_id, Inventory.product_id == product_id).first()
    if item:
        item.quantity = quantity
        db.commit()
        db.refresh(item)
        return item
    item = Inventory(warehouse_id=warehouse_id, product_id=product_id, quantity=quantity)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

