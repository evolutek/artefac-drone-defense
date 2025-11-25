"""
CRUD operations for Product model
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from ..models.product import Product
from ..models.inventory import Inventory


def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()


def get_product_by_name(db: Session, name: str) -> Optional[Product]:
    return db.query(Product).filter(Product.name == name).first()


def get_products(db: Session, skip: int = 0, limit: int = 200) -> List[Product]:
    return db.query(Product).offset(skip).limit(limit).all()


def create_product(db: Session, name: str, description: str = "", category: str = "", weight_kg: float | None = None, image_url: str | None = None) -> Product:
    p = Product(name=name, description=description, category=category, weight_kg=weight_kg, image_url=image_url)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def delete_product(db: Session, product_id: int) -> bool:
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        return False
    # Remove inventory entries referencing this product to avoid FK issues
    try:
        db.query(Inventory).filter(Inventory.product_id == product_id).delete()
    except Exception:
        pass
    db.delete(p)
    db.commit()
    return True
