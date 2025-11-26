"""
Drone Mission API - Backend
FastAPI application for drone fleet management
"""
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Header, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from .models.database import init_db, get_db, SessionLocal
from .models import Drone, Mission, Telemetry
from . import crud
from .schemas import (
    DroneCreate,
    DroneResponse,
    MissionCreate,
    MissionResponse,
    TelemetryResponse,
    HealthResponse,
    WeatherCheckRequest,
    WeatherCheckResponse,
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
    ProductCreate,
    ProductResponse,
    InventoryEntry,
    DeliveryEstimateRequest,
    DeliveryEstimateResponse,
)
from .mqtt_client import mqtt_client
from .websocket_manager import websocket_manager
from .weather_service import check_weather
from .event_bus import publish as publish_event
from .algo_service import algo_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _env_flag(name: str, default: str = "false") -> bool:
    """Parse a boolean flag from environment variables.
    Accepts true/false values like: 1, true, yes, on / 0, false, no, off.
    """
    val = os.getenv(name, default).strip().lower()
    return val in {"1", "true", "yes", "on"}

MQTT_ENABLED = _env_flag("MQTT_ENABLED", default="false")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Initialize database and MQTT client on startup
    """
    import asyncio

    logger.info("Starting application...")

    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Seed a default test drone if none exist (helps frontend connect out-of-the-box)
    try:
        db = SessionLocal()
        try:
            drones = crud.get_drones(db, skip=0, limit=1)
            if not drones:
                crud.create_drone(db, drone_id="drone-1", name="Test Drone", model="sim")
                logger.info("Seeded test drone 'drone-1' (model=sim)")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Drone seeding skipped due to error: {e}")

    # Seed SPEC French drones if database has very few entries
    try:
        db = SessionLocal()
        try:
            drones = crud.get_drones(db, skip=0, limit=5)
            if len(drones) <= 1:
                spec_drones = [
                    ("FR-PAR-001", "Paris Cargo 1", "CargoX"),
                    ("FR-LYO-002", "Lyon Cargo 2", "CargoX"),
                    ("FR-MRS-003", "Marseille Cargo 3", "CargoX"),
                    ("FR-LIL-004", "Lille Cargo 4", "CargoX"),
                    ("FR-BOD-005", "Bordeaux Cargo 5", "CargoX"),
                ]
                for did, nm, mdl in spec_drones:
                    try:
                        if not crud.get_drone(db, did):
                            crud.create_drone(db, drone_id=did, name=nm, model=mdl)
                    except Exception:
                        pass
                logger.info("Seeded SPEC drones for France")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"SPEC drone seeding skipped due to error: {e}")

    # Seed warehouses France if empty
    try:
        db = SessionLocal()
        try:
            from .crud.warehouse import get_warehouses, create_warehouse
            existing_w = get_warehouses(db, skip=0, limit=1)
            if not existing_w:
                seeds = [
                    ("Entrepôt Paris", 48.8566, 2.3522, "Paris, France"),
                    ("Entrepôt Lyon", 45.7640, 4.8357, "Lyon, France"),
                    ("Entrepôt Marseille", 43.2965, 5.3698, "Marseille, France"),
                    ("Entrepôt Lille", 50.6292, 3.0573, "Lille, France"),
                    ("Entrepôt Bordeaux", 44.8378, -0.5792, "Bordeaux, France"),
                ]
                for name, lat, lon, addr in seeds:
                    create_warehouse(db, name=name, latitude=lat, longitude=lon, address=addr)
                logger.info(f"Seeded {len(seeds)} warehouses in France")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Warehouse seeding skipped due to error: {e}")

    # Seed products from frontend catalog if empty
    try:
        db = SessionLocal()
        try:
            from .crud.product import get_products, create_product, get_product_by_name
            existing_p = get_products(db, skip=0, limit=1)
            if not existing_p:
                catalog = [
                    ("Batterie 4S 5000mAh", "Batterie LiPo haute capacité", "", 0.45, None),
                    ("Capteur météo", "Module de mesure météo", "", 0.12, None),
                    ("Kit secours", "Kit de premiers secours", "", 1.2, None),
                    ("Caméra HD", "Caméra 1080p stabilisée", "", 0.2, None),
                    ("Boîte pharma A", "Médicaments urgences A", "", 0.8, None),
                    ("Boîte pharma B", "Médicaments urgences B", "", 0.9, None),
                    ("Capteur gaz", "Détection gaz industriels", "", 0.15, None),
                    ("Rations MRE", "Rations prêtes à consommer", "", 2.0, None),
                    ("Pièces moteur", "Pièces détachées moteur", "", 1.8, None),
                    ("Module GPS", "Module positionnement haute précision", "", 0.1, None),
                ]
                for name, desc, cat, weight, image in catalog:
                    try:
                        if not get_product_by_name(db, name):
                            create_product(db, name=name, description=desc, category=cat, weight_kg=weight, image_url=image)
                    except Exception:
                        pass
                logger.info(f"Seeded {len(catalog)} products from frontend catalog")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Product seeding skipped due to error: {e}")

    # Seed mocked frontend products (upsert by name)
    try:
        db = SessionLocal()
        try:
            from .crud.product import create_product, get_product_by_name
            mock_catalog = [
                ("Munitions 5.56mm", "Caisses de 1000 cartouches 5.56mm", "munitions", 15, "/products/ammo-556.svg"),
                ("Munitions 9mm", "Caisses de 1000 cartouches 9mm", "munitions", 12, "/products/ammo-9mm.svg"),
                ("Kit Médical Avancé", "Pansements, garrots, antiseptiques", "medicaments", 8, "/products/med-kit.svg"),
                ("Viseur Optique X", "Viseur optique compatible rails Picatinny", "attachments", 1.2, "/products/optic-x.svg"),
                ("Radio cryptée", "Radio longue portée, chiffrement intégré", "communication", 2.4, "/products/radio-secure.svg"),
                ("Pack Énergie", "Batteries portables haute capacité", "logistique", 20, "/products/power-pack.svg"),
                ("Carburant en jerrican 20L", "Jerrican 20L (diesel) — ~18 kg", "logistique", 18, "/products/fuel-jerrycan-20l.svg"),
                ("Eau potable jerrican 20L", "Jerrican 20L eau — ~20 kg", "logistique", 20, "/products/water-jerrycan-20l.svg"),
                ("Pack eau 6×1.5L", "Pack de 6 bouteilles 1.5L — ~9 kg", "logistique", 9, "/products/water-pack-6x1.5l.svg"),
                ("Rations MRE (boîte)", "Boîte de rations MRE — ~2.5 kg", "logistique", 2.5, "/products/food-mre-box.svg"),
                ("Kit nourriture déshydratée", "Plats lyophilisés variés — ~6 kg", "logistique", 6, "/products/food-dry-kit.svg"),
                ("Kit hygiène complet", "Savon, lingettes, brosse à dents, papier, gel hydro", "logistique", 3, "/products/hygiene-kit.svg"),
                ("Grenade offensive", "Grenade offensive (onde de choc, faible fragmentation)", "munitions", 0.45, "/products/grenade-offensive.svg"),
                ("Grenade défensive (frag)", "Grenade à fragmentation (défensive)", "munitions", 0.6, "/products/grenade-frag.svg"),
                ("Grenade fumigène", "Grenade fumigène multi-couleurs", "munitions", 0.4, "/products/grenade-smoke.svg"),
                ("Grenade flash (stun)", "Grenade assourdissante (flashbang)", "munitions", 0.3, "/products/grenade-flash.svg"),
                ("Hélices renforcées (set de 4)", "Jeu de 4 hélices carbone renforcées", "logistique", 0.5, "/products/propeller-reinforced.svg"),
                ("Moteur brushless 2212", "Moteur 2212 KV920 pour drone multirotor", "logistique", 0.08, "/products/motor-brushless.svg"),
                ("ESC 30A", "Contrôleur électronique de vitesse 30A", "logistique", 0.05, "/products/esc-30a.svg"),
                ("Kit visserie inox", "Assortiment de vis/écrous/entretoises inox", "logistique", 0.4, "/products/screw-kit.svg"),
                ("Extincteur CO2 2kg", "Extincteur CO2 2kg pour feux B/électriques", "logistique", 6, "/products/extinguisher-co2-2kg.svg"),
                ("Extincteur poudre 6kg", "Extincteur poudre polyvalent ABC 6kg", "logistique", 9, "/products/extinguisher-powder-6kg.svg"),
                ("Aérosol anti-feu 1L", "Aérosol extincteur portable 1L", "logistique", 1.2, "/products/extinguisher-aerosol-1l.svg"),
            ]
            added = 0
            for name, desc, cat, weight, image in mock_catalog:
                try:
                    if not get_product_by_name(db, name):
                        create_product(db, name=name, description=desc, category=cat, weight_kg=weight, image_url=image)
                        added += 1
                except Exception:
                    pass
            if added:
                logger.info(f"Seeded {added} mocked frontend products into backoffice")
            else:
                logger.info("Mocked frontend products already present; no new insertions")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Mocked product seeding skipped due to error: {e}")

    # Ensure placeholder images for products missing image_url
    try:
        db = SessionLocal()
        try:
            from .crud.product import get_products
            prods = get_products(db, skip=0, limit=10000)
            changed = 0
            for prod in prods:
                if not getattr(prod, "image_url", None):
                    prod.image_url = f"/product-placeholder/{prod.id}.svg"
                    changed += 1
            if changed:
                db.commit()
                logger.info(f"Assigned placeholder images to {changed} products")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Assigning placeholder images skipped due to error: {e}")

    # Start MQTT client if enabled
    if MQTT_ENABLED:
        logger.info("Starting MQTT client (enabled by env)...")
        mqtt_client.start()

        # Setup MQTT callbacks for WebSocket broadcasting with the main event loop
        from .websocket_manager import setup_mqtt_callbacks
        event_loop = asyncio.get_event_loop()
        setup_mqtt_callbacks(event_loop)
    else:
        logger.info("MQTT disabled (set MQTT_ENABLED=true to enable). Backend will still run.")

    # Start gRPC realtime server (for gRPC clients)
    try:
        from .grpc_server import serve_grpc
        grpc_task = asyncio.create_task(serve_grpc(port=50051))
        app.state.grpc_task = grpc_task
        logger.info("gRPC realtime server started on :50051")
    except Exception as e:
        logger.error(f"Failed to start gRPC server: {e}")

    # Start C algorithm service
    try:
        if algo_service.start():
            logger.info("C algorithm service started successfully")

            # Seed existing data to algorithm
            db = SessionLocal()
            try:
                # Send all products
                from .crud.product import get_products
                products = get_products(db, skip=0, limit=1000)
                for prod in products:
                    algo_service.send_item_new(prod)

                # Send all warehouses
                from .crud.warehouse import get_warehouses
                warehouses = get_warehouses(db, skip=0, limit=1000)
                for wh in warehouses:
                    algo_service.send_warehouse_new(wh)

                # Send all drones
                drones = crud.get_drones(db, skip=0, limit=1000)
                for drone in drones:
                    algo_service.send_drone_new(drone)

                logger.info("Synchronized existing data with C algorithm")
            finally:
                db.close()
        else:
            logger.warning("C algorithm service failed to start - running without optimization")
    except Exception as e:
        logger.error(f"Failed to start C algorithm service: {e}")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application...")
    if MQTT_ENABLED:
        mqtt_client.stop()
    # Stop gRPC server
    try:
        task = getattr(app.state, 'grpc_task', None)
        if task:
            task.cancel()
    except Exception:
        pass
    # Stop C algorithm
    try:
        algo_service.stop()
    except Exception as e:
        logger.error(f"Error stopping algo service: {e}")


app = FastAPI(
    title="Drone Mission API",
    description="Backend for drone fleet management and mission planning",
    version="1.0.0-mvp",
    lifespan=lifespan,
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount backoffice static UI at /admin if directory exists
try:
    app.mount("/admin", StaticFiles(directory="backoffice", html=True), name="admin")
    logger.info("Backoffice mounted at /admin")
except Exception as e:
    logger.warning(f"Failed to mount backoffice: {e}")

# Serve product icons from techinal_map for backoffice display (avoid API route collision)
try:
    app.mount("/product-icons", StaticFiles(directory="techinal_map/public/products"), name="product-icons")
    logger.info("Product icons mounted at /product-icons")
except Exception as e:
    logger.warning(f"Failed to mount product icons: {e}")


# ==================== Health Check ====================

@app.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    Returns status of backend, database, MQTT connection, and connected drones
    """
    # Check MQTT connection
    mqtt_status = mqtt_client.is_connected()

    # Count connected drones
    drones = crud.get_drones(db)
    connected_drones = len([d for d in drones if d.status == "connected"])

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "mqtt_connected": mqtt_status,
        "database": "operational",
        "drones_connected": connected_drones,
    }


# ==================== Drone Endpoints ====================

@app.post("/drones", response_model=DroneResponse)
def register_drone(drone: DroneCreate, db: Session = Depends(get_db)):
    """
    Register a new drone
    """
    # Check if drone already exists
    existing = crud.get_drone(db, drone.drone_id)
    if existing:
        raise HTTPException(status_code=400, detail="Drone already registered")

    db_drone = crud.create_drone(
        db,
        drone_id=drone.drone_id,
        name=drone.name,
        model=drone.model,
    )
    logger.info(f"Registered drone: {drone.drone_id}")

    # Send to C algorithm
    try:
        algo_service.send_drone_new(db_drone)
    except Exception as e:
        logger.warning(f"Failed to send drone to algorithm: {e}")

    # Broadcast state for real-time backoffice refresh via event bus
    try:
        evt = {"type": "drone_upsert", "drone": {
            "drone_id": db_drone.drone_id,
            "name": db_drone.name,
            "model": db_drone.model,
            "status": db_drone.status,
            "battery_level": db_drone.battery_level,
        }}
        publish_event({"type": "state", "drone_id": drone.drone_id, "data": evt})
    except Exception as e:
        logger.warning(f"Failed to publish drone upsert event: {e}")
    return db_drone


@app.get("/drones", response_model=List[DroneResponse])
def list_drones(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List all registered drones
    """
    drones = crud.get_drones(db, skip=skip, limit=limit)
    return drones


@app.get("/drones/{drone_id}", response_model=DroneResponse)
def get_drone(drone_id: str, db: Session = Depends(get_db)):
    """
    Get drone details
    """
    drone = crud.get_drone(db, drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")
    return drone


@app.get("/drones/{drone_id}/telemetry", response_model=TelemetryResponse)
def get_drone_telemetry(drone_id: str, db: Session = Depends(get_db)):
    """
    Get latest telemetry for a drone
    """
    telemetry = crud.get_latest_telemetry(db, drone_id)
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry data available")
    return telemetry


@app.post("/drones/{drone_id}/arm")
def arm_drone(drone_id: str, db: Session = Depends(get_db)):
    """
    Arm drone motors
    Publishes ARM command to MQTT and waits for result
    """
    drone = crud.get_drone(db, drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

    # Publish ARM command via MQTT
    success = mqtt_client.publish_command(drone_id, "ARM")
    if not success:
        raise HTTPException(status_code=503, detail="MQTT broker not available")

    logger.info(f"ARM command sent to {drone_id}, waiting for result...")

    # Wait for command result from ROS2 bridge
    result = mqtt_client.wait_for_command_result(drone_id, "ARM", timeout=5.0)

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Timeout waiting for drone response - check if ROS2 bridge is running"
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "ARM command failed")
        )

    return {
        "success": True,
        "message": result.get("message", "Drone armed successfully")
    }


@app.post("/drones/{drone_id}/disarm")
def disarm_drone(drone_id: str, db: Session = Depends(get_db)):
    """
    Disarm drone motors
    Publishes DISARM command to MQTT and waits for result
    """
    drone = crud.get_drone(db, drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

    # Publish DISARM command via MQTT
    success = mqtt_client.publish_command(drone_id, "DISARM")
    if not success:
        raise HTTPException(status_code=503, detail="MQTT broker not available")

    logger.info(f"DISARM command sent to {drone_id}, waiting for result...")

    # Wait for command result from ROS2 bridge
    result = mqtt_client.wait_for_command_result(drone_id, "DISARM", timeout=5.0)

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Timeout waiting for drone response - check if ROS2 bridge is running"
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "DISARM command failed")
        )

    return {
        "success": True,
        "message": result.get("message", "Drone disarmed successfully")
    }


@app.post("/drones/{drone_id}/takeoff")
def takeoff_drone(drone_id: str, altitude: float = 5.0, db: Session = Depends(get_db)):
    """
    Command drone to takeoff
    Publishes TAKEOFF command to MQTT with altitude parameter and waits for result
    """
    drone = crud.get_drone(db, drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

    # Publish TAKEOFF command via MQTT
    success = mqtt_client.publish_command(drone_id, "TAKEOFF", {"altitude": altitude})
    if not success:
        raise HTTPException(status_code=503, detail="MQTT broker not available")

    logger.info(f"TAKEOFF command sent to {drone_id} (altitude: {altitude}m), waiting for result...")

    # Wait for command result from ROS2 bridge
    result = mqtt_client.wait_for_command_result(drone_id, "TAKEOFF", timeout=5.0)

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Timeout waiting for drone response - check if ROS2 bridge is running"
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "TAKEOFF command failed")
        )

    return {
        "success": True,
        "message": result.get("message", "Takeoff command sent successfully"),
        "altitude": altitude
    }


@app.post("/drones/{drone_id}/land")
def land_drone(drone_id: str, db: Session = Depends(get_db)):
    """
    Command drone to land
    Publishes LAND command to MQTT and waits for result
    """
    drone = crud.get_drone(db, drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

    # Publish LAND command via MQTT
    success = mqtt_client.publish_command(drone_id, "LAND")
    if not success:
        raise HTTPException(status_code=503, detail="MQTT broker not available")

    logger.info(f"LAND command sent to {drone_id}, waiting for result...")

    # Wait for command result from ROS2 bridge
    result = mqtt_client.wait_for_command_result(drone_id, "LAND", timeout=5.0)

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Timeout waiting for drone response - check if ROS2 bridge is running"
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "LAND command failed")
        )

    return {
        "success": True,
        "message": result.get("message", "Land command sent successfully")
    }


# ==================== Mission Endpoints ====================

@app.post("/missions", response_model=MissionResponse)
def create_mission(mission: MissionCreate, db: Session = Depends(get_db)):
    """
    Create new mission
    """
    # Verify drone exists
    drone = crud.get_drone(db, mission.drone_id)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")

    # Convert waypoints to JSON string if needed
    import json
    waypoints_json = json.dumps(mission.waypoints) if mission.waypoints else None
    payload_json = json.dumps(mission.payload) if mission.payload else None
    payloads_json = json.dumps(mission.payloads) if mission.payloads else None

    db_mission = crud.create_mission(
        db,
        drone_id=mission.drone_id,
        mission_type=mission.mission_type,
        waypoints=waypoints_json,
        payload=payload_json,
        payloads=payloads_json,
        note=mission.note,
        priority=mission.priority,
    )
    # Météo: évaluer le risque de façon informative uniquement.
    # L'état de mission NE DOIT PAS être modifié automatiquement ici.
    try:
        first_wp = None
        if mission.waypoints and len(mission.waypoints) > 0:
            wp0 = mission.waypoints[0]
            lat = wp0.get("lat")
            lon = wp0.get("lon")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                first_wp = (float(lat), float(lon))

        if first_wp:
            assessment = check_weather(first_wp[0], first_wp[1])
            logger.info(
                f"Mission {db_mission.id} météo: risk={assessment.risk} wind={assessment.metrics.wind_speed}m/s gusts={assessment.metrics.wind_gusts}m/s rain={assessment.metrics.precipitation}mm/h"
            )
            # Décision météo laissée à l'opérateur dans le backoffice.
    except Exception as e:
        # Ne jamais échouer la création pour un problème météo
        logger.warning(f"Weather check failed for mission {db_mission.id}: {e}")

    logger.info(f"Created mission {db_mission.id} for drone {mission.drone_id}")

    # Send mission to C algorithm for optimization
    # If multiple products are requested, send one delivery per product type
    try:
        payloads = json.loads(payloads_json) if payloads_json else []
        if not payloads:
            # No specific payloads, send the mission as-is
            algo_service.send_delivery_new(db_mission, db_session=db)
            logger.info(f"Sent mission {db_mission.id} to algorithm for processing")
        else:
            # Send one delivery per product type
            for idx, payload_item in enumerate(payloads):
                # Create a temporary mission-like object for each product
                class DeliveryForAlgo:
                    def __init__(self, mission_id, waypoints, priority, payload_data):
                        self.id = mission_id * 1000 + idx  # Unique ID per delivery
                        self.waypoints = waypoints
                        self.priority = priority
                        self.payload_item = payload_data

                delivery = DeliveryForAlgo(db_mission.id, waypoints_json, db_mission.priority or 0, payload_item)
                algo_service.send_delivery_new(delivery, db_session=db)
                logger.info(f"Sent delivery {delivery.id} (product: {payload_item.get('item_name')}) to algorithm")
    except Exception as e:
        logger.error(f"Failed to send mission {db_mission.id} to algorithm: {e}")

    # Broadcast mission creation for real-time backoffice refresh via event bus
    try:
        evt = {"type": "mission_upsert", "mission_id": db_mission.id}
        publish_event({"type": "state", "drone_id": "system", "data": evt})
    except Exception as e:
        logger.warning(f"Failed to publish mission_upsert event for mission {db_mission.id}: {e}")

    return db_mission


@app.get("/missions", response_model=List[MissionResponse])
def list_missions(
    drone_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List missions with optional filters
    """
    missions = crud.get_missions(db, drone_id=drone_id, status=status, skip=skip, limit=limit)
    return missions


@app.get("/missions/{mission_id}", response_model=MissionResponse)
def get_mission(mission_id: int, db: Session = Depends(get_db)):
    """
    Get mission details
    """
    mission = crud.get_mission(db, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@app.put("/missions/{mission_id}/status")
def update_mission_status(mission_id: int, status: str, db: Session = Depends(get_db), x_idempotency_key: str | None = Header(default=None)):
    """
    Update mission status
    """
    # Idempotency guard (optional)
    if x_idempotency_key:
        try:
            from .crud.idempotency import has_key, record_key
            scope = f"mission_status:{mission_id}:{status}"
            if has_key(db, scope, x_idempotency_key):
                logger.info(f"Idempotent replay ignored for scope={scope} key={x_idempotency_key}")
                return {"message": f"Mission {mission_id} status updated to {status} (idempotent)"}
        except Exception:
            pass

    mission = crud.update_mission_status(db, mission_id, status)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    logger.info(f"Mission {mission_id} status updated to {status}")
    # Broadcast mission status change via event bus
    try:
        evt = {"type": "mission_status_update", "mission_id": mission_id, "status": status}
        publish_event({"type": "state", "drone_id": "system", "data": evt})
    except Exception as e:
        logger.warning(f"Failed to publish mission status update event: {e}")

    # Record idempotency key after successful update
    if x_idempotency_key:
        try:
            from .crud.idempotency import record_key
            scope = f"mission_status:{mission_id}:{status}"
            record_key(db, scope, x_idempotency_key)
        except Exception:
            pass
    return {"message": f"Mission {mission_id} status updated to {status}"}


@app.put("/missions/{mission_id}/note")
def update_mission_note(mission_id: int, note: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Update mission operator note. Accepts note as query parameter.
    """
    mission = crud.update_mission_note(db, mission_id, note)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    logger.info(f"Mission {mission_id} note updated")
    # Broadcast mission note change via event bus
    try:
        evt = {"type": "mission_note_update", "mission_id": mission_id}
        publish_event({"type": "state", "drone_id": "system", "data": evt})
    except Exception as e:
        logger.warning(f"Failed to publish mission note update event: {e}")
    return {"message": f"Mission {mission_id} note updated"}


@app.delete("/missions/{mission_id}")
def delete_mission_endpoint(mission_id: int, db: Session = Depends(get_db)):
    """
    Delete a mission and broadcast deletion event
    """
    mission = crud.get_mission(db, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    deleted = crud.delete_mission(db, mission_id)
    logger.info(f"Mission {mission_id} deleted")

    # Send REMOVE event to C algorithm
    try:
        algo_service.send_delivery_remove(mission_id)
    except Exception as e:
        logger.warning(f"Failed to send delivery remove to algorithm: {e}")

    # Broadcast mission deletion via event bus
    try:
        evt = {"type": "mission_delete", "mission_id": mission_id}
        publish_event({"type": "state", "drone_id": "system", "data": evt})
    except Exception as e:
        logger.warning(f"Failed to publish mission delete event: {e}")

    return {"message": f"Mission {mission_id} deleted"}


# ==================== Weather Endpoints ====================

@app.get("/weather/check", response_model=WeatherCheckResponse)
def weather_check(lat: float, lon: float):
    """
    Evaluate weather risk at given coordinates. Returns a simple risk category
    and metrics. This endpoint is additive and does not impact other services.
    """
    assessment = check_weather(lat, lon)
    # Map dataclasses to Pydantic response
    return WeatherCheckResponse(
        risk=assessment.risk,
        reason=assessment.reason,
        metrics={
            "wind_speed": assessment.metrics.wind_speed,
            "wind_gusts": assessment.metrics.wind_gusts,
            "precipitation": assessment.metrics.precipitation,
            "temperature": assessment.metrics.temperature,
            "timestamp": assessment.metrics.timestamp,
        },
    )


# ==================== WebSocket Endpoints ====================

@app.websocket("/ws/telemetry")
async def websocket_telemetry_all(websocket: WebSocket):
    """
    WebSocket endpoint for real-time telemetry from all drones
    """
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and wait for disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


@app.websocket("/ws/drone/{drone_id}")
async def websocket_telemetry_drone(websocket: WebSocket, drone_id: str):
    """
    WebSocket endpoint for real-time telemetry from specific drone
    """
    await websocket_manager.connect(websocket, drone_id)
    try:
        while True:
            # Keep connection alive and wait for disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, drone_id)


# ==================== Warehouse & Product Endpoints ====================

@app.get("/warehouses", response_model=List[WarehouseResponse])
def list_warehouses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    from .crud.warehouse import get_warehouses
    return get_warehouses(db, skip=skip, limit=limit)


@app.post("/warehouses", response_model=WarehouseResponse)
def create_warehouse_endpoint(payload: WarehouseCreate, db: Session = Depends(get_db)):
    from .crud.warehouse import create_warehouse
    w = create_warehouse(db, name=payload.name, latitude=payload.latitude, longitude=payload.longitude, address=payload.address, capacity=payload.capacity)

    # Send to C algorithm
    try:
        algo_service.send_warehouse_new(w)
    except Exception as e:
        logger.warning(f"Failed to send warehouse to algorithm: {e}")

    # Broadcast state for real-time backoffice refresh via event bus
    try:
        evt = {"type": "warehouse_upsert", "warehouse": {
            "id": w.id,
            "name": w.name,
            "latitude": w.latitude,
            "longitude": w.longitude,
            "address": w.address,
            "capacity": getattr(w, "capacity", None),
            "status": getattr(w, "status", None),
            "note": getattr(w, "note", None),
        }}
        publish_event({"type": "state", "drone_id": "system", "data": evt})
    except Exception as e:
        logger.warning(f"Failed to publish warehouse upsert event: {e}")
    return w


@app.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse_endpoint(warehouse_id: int, payload: WarehouseUpdate, db: Session = Depends(get_db)):
    from .crud.warehouse import update_warehouse
    fields = payload.model_dump(exclude_unset=True)
    w = update_warehouse(db, warehouse_id, **fields)
    if not w:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    try:
        import asyncio
        evt = {"type": "warehouse_upsert", "warehouse": {
            "id": w.id,
            "name": w.name,
            "latitude": w.latitude,
            "longitude": w.longitude,
            "address": w.address,
            "capacity": getattr(w, "capacity", None),
            "status": getattr(w, "status", None),
            "note": getattr(w, "note", None),
        }}
        asyncio.create_task(websocket_manager.broadcast_state("system", evt))
        publish_event({"type": "state", "drone_id": "system", "data": evt})
    except Exception:
        pass
    return w


@app.get("/products", response_model=List[ProductResponse])
def list_products(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    from .crud.product import get_products
    items = get_products(db, skip=skip, limit=limit)
    # Ensure image_url is set for any legacy rows
    updated = False
    for it in items:
        if not getattr(it, "image_url", None):
            it.image_url = f"/product-placeholder/{it.id}.svg"
            updated = True
    if updated:
        try:
            db.commit()
        except Exception:
            pass
    return items


@app.post("/products", response_model=ProductResponse)
def create_product_endpoint(payload: ProductCreate, db: Session = Depends(get_db)):
    from .crud.product import create_product, get_product_by_name
    existing = get_product_by_name(db, payload.name)
    if existing:
        raise HTTPException(status_code=400, detail="Product already exists")
    p = create_product(db, name=payload.name, description=payload.description or "", category=payload.category or "", weight_kg=payload.weight_kg, image_url=payload.image_url)
    # If no image provided, assign dynamic placeholder
    if not p.image_url:
        p.image_url = f"/product-placeholder/{p.id}.svg"
        try:
            db.add(p)
            db.commit()
            db.refresh(p)
        except Exception:
            pass

    # Send to C algorithm
    try:
        algo_service.send_item_new(p)
    except Exception as e:
        logger.warning(f"Failed to send product to algorithm: {e}")

    # Broadcast state for real-time backoffice refresh via event bus
    try:
        evt = {"type": "product_upsert", "product": {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "weight_kg": p.weight_kg,
            "image_url": p.image_url,
        }}
        publish_event({"type": "state", "drone_id": "system", "data": evt})
    except Exception as e:
        logger.warning(f"Failed to publish product upsert event: {e}")
    return p


@app.delete("/products/{product_id}")
def delete_product_endpoint(product_id: int, db: Session = Depends(get_db)):
    from .crud.product import delete_product
    ok = delete_product(db, product_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Product not found")

    # Send REMOVE event to C algorithm
    try:
        algo_service.send_item_remove(product_id)
    except Exception as e:
        logger.warning(f"Failed to send item remove to algorithm: {e}")

    # Broadcast state for real-time backoffice refresh via event bus
    try:
        evt = {"type": "product_delete", "product_id": product_id}
        publish_event({"type": "state", "drone_id": "system", "data": evt})
    except Exception as e:
        logger.warning(f"Failed to publish product delete event: {e}")
    return {"message": f"Product {product_id} deleted"}


@app.get("/product-placeholder/{product_id}.svg")
def product_placeholder_svg(product_id: int, db: Session = Depends(get_db)):
    from .crud.product import get_product
    p = get_product(db, product_id)
    name = (p.name if p else f"Produit {product_id}").strip()
    category = (p.category if p and p.category else "").strip().lower()
    color_map = {
        "munitions": "#F97316",      # orange
        "attachments": "#22C55E",    # green
        "medicaments": "#EF4444",    # red
        "communication": "#0EA5E9",  # sky
        "logistique": "#8B5CF6",    # violet
    }
    base_color = color_map.get(category, "#64748B")  # slate
    svg = f"""
<svg xmlns='http://www.w3.org/2000/svg' width='512' height='512' viewBox='0 0 512 512'>
  <defs>
    <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
      <stop offset='0' stop-color='{base_color}' stop-opacity='0.9'/>
      <stop offset='1' stop-color='#111827' stop-opacity='0.9'/>
    </linearGradient>
  </defs>
  <rect x='0' y='0' width='512' height='512' fill='url(#g)'/>
  <rect x='24' y='24' width='464' height='464' rx='28' ry='28' fill='rgba(255,255,255,0.08)' stroke='rgba(255,255,255,0.2)'/>
  <text x='256' y='260' font-size='36' fill='#FFFFFF' text-anchor='middle' font-family='Inter, system-ui, sans-serif'>{name}</text>
  <text x='256' y='304' font-size='16' fill='rgba(255,255,255,0.75)' text-anchor='middle' font-family='Inter, system-ui, sans-serif'>{category or 'produit'}</text>
</svg>
"""
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/warehouses/{warehouse_id}/inventory")
def get_inventory(warehouse_id: int, db: Session = Depends(get_db)):
    from .crud.inventory import get_inventory_for_warehouse
    items = get_inventory_for_warehouse(db, warehouse_id)
    return [{
        "product_id": it.product_id,
        "quantity": it.quantity,
        "product": {
            "id": it.product.id,
            "name": it.product.name,
            "category": it.product.category,
            "weight_kg": it.product.weight_kg,
            "image_url": it.product.image_url,
        }
    } for it in items]


@app.post("/warehouses/{warehouse_id}/inventory")
def upsert_inventory(warehouse_id: int, entry: InventoryEntry, db: Session = Depends(get_db)):
    from .crud.inventory import upsert_inventory
    # ensure product exists
    from .crud.product import get_product
    p = get_product(db, entry.product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    item = upsert_inventory(db, warehouse_id=warehouse_id, product_id=entry.product_id, quantity=entry.quantity)
    # Broadcast state for real-time backoffice refresh via event bus
    try:
        evt = {"type": "inventory_update", "inventory": {
            "warehouse_id": warehouse_id,
            "product_id": item.product_id,
            "quantity": item.quantity,
        }}
        publish_event({"type": "state", "drone_id": "system", "data": evt})
    except Exception as e:
        logger.warning(f"Failed to publish inventory update event: {e}")
    return {"product_id": item.product_id, "quantity": item.quantity}


# ==================== Delivery Estimation ====================

@app.get("/algo/assignment")
def get_algo_assignment():
    """
    Get the next assignment from the C algorithm.
    This endpoint blocks until the algorithm produces a result.
    Use with caution as it may timeout if algorithm is not running.
    """
    try:
        mission = algo_service.get_assignment()
        if mission is None:
            raise HTTPException(status_code=503, detail="Algorithm not available or failed to get assignment")

        return {
            "mission_id": mission.mission_id,
            "drone_id": mission.drone_id,
            "waypoints": [
                {
                    "position": {"x": wp.position[0], "y": wp.position[1]},
                    "type": wp.type
                }
                for wp in mission.waypoints
            ]
        }
    except Exception as e:
        logger.error(f"Error getting assignment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get assignment: {str(e)}")


@app.post("/estimate_delivery", response_model=DeliveryEstimateResponse)
def estimate_delivery(req: DeliveryEstimateRequest, db: Session = Depends(get_db)):
    import math

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
        c = 2*math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    distance_m = haversine(req.origin_lat, req.origin_lon, req.dest_lat, req.dest_lon)

    # Base speed heuristic (m/s)
    base_speed = 12.0
    if req.drone_id:
        # Could lookup model-specific speed in DB; keep simple for now
        pass

    # Weather impact at destination
    assessment = check_weather(req.dest_lat, req.dest_lon)
    risk = assessment.risk
    reason = assessment.reason

    # Adjust speed based on risk and payload weight
    speed_factor = 1.0
    if risk == "caution":
        speed_factor *= 0.75
    elif risk == "blocked":
        # No ETA if blocked
        return {
            "distance_m": distance_m,
            "eta_minutes": None,
            "risk": risk,
            "reason": reason,
            "recommended_speed_mps": None,
            "required_autonomy_minutes": None,
        }

    # Payload effect: -5% per kg up to -50%
    weight_penalty = min(0.5, max(0.0, 0.05 * req.payload_weight_kg))
    speed_factor *= (1.0 - weight_penalty)

    recommended_speed = max(4.0, base_speed * speed_factor)
    eta_seconds = distance_m / recommended_speed if recommended_speed > 0 else 0
    eta_minutes = round(eta_seconds / 60.0, 2)

    # Required autonomy adds 10% safety margin
    required_autonomy_minutes = round(eta_minutes * 1.1, 2)

    return {
        "distance_m": distance_m,
        "eta_minutes": eta_minutes,
        "risk": risk,
        "reason": reason,
        "recommended_speed_mps": recommended_speed,
        "required_autonomy_minutes": required_autonomy_minutes,
    }
