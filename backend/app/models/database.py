"""
Database configuration and session management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend_data/app.db")

# Create engine
# For SQLite, we need check_same_thread=False to allow multiple threads
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
# Ensure SQLite directory exists if using a file path
if DATABASE_URL.startswith("sqlite"):
    # Expected formats: sqlite:///relative/path.db or sqlite:////absolute/path.db
    db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite:////", "/")
    dir_path = os.path.dirname(db_path) or "."
    try:
        os.makedirs(dir_path, exist_ok=True)
    except Exception:
        # Directory creation failure will be surfaced by engine connect later
        pass

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI routes to get database session
    Usage: def endpoint(db: Session = Depends(get_db))
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables
    Should be called at application startup
    """
    # Import all models here to ensure they are registered with Base
    from . import drone, mission, telemetry, warehouse, product, inventory, idempotency  # noqa: F401

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Lightweight migration for missions payload columns (SQLite only)
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            cols = conn.execute(text("PRAGMA table_info(missions)")).fetchall()
            existing = {row[1] for row in cols}  # row schema: (cid, name, type, ...)
            if "payload" not in existing:
                conn.execute(text("ALTER TABLE missions ADD COLUMN payload TEXT"))
            if "payloads" not in existing:
                conn.execute(text("ALTER TABLE missions ADD COLUMN payloads TEXT"))
            if "note" not in existing:
                conn.execute(text("ALTER TABLE missions ADD COLUMN note TEXT"))
            # Warehouses: add status and note columns if missing
            cols_w = conn.execute(text("PRAGMA table_info(warehouses)")).fetchall()
            existing_w = {row[1] for row in cols_w}
            if "status" not in existing_w:
                conn.execute(text("ALTER TABLE warehouses ADD COLUMN status TEXT"))
            if "note" not in existing_w:
                conn.execute(text("ALTER TABLE warehouses ADD COLUMN note TEXT"))
    except Exception:
        # Non-blocking: migrations best-effort; if it fails, creation still works
        pass
