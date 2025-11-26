"""
Service pour gérer le processus de l'algorithme C et la communication IPC
"""
import subprocess
import logging
import atexit
from pathlib import Path
from typing import Optional

from .algo_interface import (
    algo_interface_init,
    algo_interface_cleanup,
    get_assignment,
    new_event,
    EventType,
    Drone as AlgoDrone,
    Delivery as AlgoDelivery,
    Warehouse as AlgoWarehouse,
    Item as AlgoItem,
)

logger = logging.getLogger(__name__)


class AlgoService:
    """Service to manage the C algorithm process and IPC communication"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.interface = None

    def start(self):
        """Start the C algorithm and initialize IPC interface"""
        # Path to C executable
        algo_path = Path(__file__).parent / "logic" / "build" / "algo"

        if not algo_path.exists():
            logger.error(f"Algo executable not found at {algo_path}")
            logger.error("Please compile with: cd backend/app/logic && make all")
            return False

        try:
            # Initialize Python interface (creates semaphores and shared memory)
            logger.info("Initializing algo interface...")
            self.interface = algo_interface_init()

            # Launch C process
            logger.info(f"Starting C algorithm: {algo_path}")
            self.process = subprocess.Popen(
                [str(algo_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            logger.info(f"C algorithm started with PID {self.process.pid}")

            # Register cleanup on exit
            atexit.register(self.stop)

            return True

        except Exception as e:
            logger.error(f"Failed to start algo service: {e}")
            return False

    def stop(self):
        """Stop the algorithm and cleanup resources"""
        if self.process:
            logger.info("Stopping C algorithm...")
            try:
                # Send EVENT_STOP via shared memory
                algo_interface_cleanup()
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")

            # Wait for process to terminate
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Algorithm did not stop gracefully, killing...")
                self.process.kill()

            self.process = None
            logger.info("C algorithm stopped")

    def send_drone_new(self, drone_data):
        """Send DRONE_NEW event to the algorithm"""
        try:
            algo_drone = AlgoDrone(
                id=hash(drone_data.drone_id) % (2**32),  # Convert string ID to uint64
                position=(drone_data.position_x or 0.0, drone_data.position_y or 0.0),
                max_capacity=int(getattr(drone_data, 'max_capacity', 1000)),
                energy=drone_data.battery_level or 100.0,
                max_flight_time=int(getattr(drone_data, 'max_flight_time', 1800)),
                max_speed=int(getattr(drone_data, 'max_speed', 15)),
                acceleration=int(getattr(drone_data, 'acceleration', 2)),
            )
            new_event(EventType.EVENT_DRONE_NEW, algo_drone)
            logger.info(f"Sent DRONE_NEW event for {drone_data.drone_id}")
        except Exception as e:
            logger.error(f"Failed to send DRONE_NEW event: {e}")

    def send_delivery_new(self, delivery_data, db_session=None):
        """Send DELIVERY_NEW event to the algorithm"""
        try:
            # Extract coordinates from first waypoint if available
            import json
            waypoints = json.loads(delivery_data.waypoints) if delivery_data.waypoints else []
            if waypoints:
                lat = waypoints[0].get('lat', 0.0)
                lon = waypoints[0].get('lon', 0.0)
            else:
                lat, lon = 0.0, 0.0

            # Extract quantity and item_id from payload_item if available
            quantity = 1
            item_id = 1

            if hasattr(delivery_data, 'payload_item') and delivery_data.payload_item:
                payload = delivery_data.payload_item
                quantity = payload.get('quantity', 1)
                item_name = payload.get('item_name', '')

                # Map item_name to item_id using the database
                if db_session and item_name:
                    try:
                        from .crud.product import get_product_by_name
                        product = get_product_by_name(db_session, item_name)
                        if product:
                            item_id = product.id
                        else:
                            logger.warning(f"Product '{item_name}' not found in database, using default item_id=1")
                    except Exception as e:
                        logger.warning(f"Failed to lookup product '{item_name}': {e}, using default item_id=1")

            algo_delivery = AlgoDelivery(
                id=delivery_data.id,
                position=(lat, lon),
                priority=delivery_data.priority or 5,
                user_priority=delivery_data.priority or 5,
                quantity=quantity,
                item_id=item_id,
            )
            new_event(EventType.EVENT_DELIVERY_NEW, algo_delivery)
            logger.info(f"Sent DELIVERY_NEW event for delivery {delivery_data.id} (item_id={item_id}, quantity={quantity})")
        except Exception as e:
            logger.error(f"Failed to send DELIVERY_NEW event: {e}")

    def send_warehouse_new(self, warehouse_data):
        """Send WAREHOUSE_NEW event to the algorithm"""
        try:
            algo_warehouse = AlgoWarehouse(
                id=warehouse_data.id,
                position=(warehouse_data.latitude, warehouse_data.longitude),
                item_ids=[],  # Would populate from inventory
            )
            new_event(EventType.EVENT_WAREHOUSE_NEW, algo_warehouse)
            logger.info(f"Sent WAREHOUSE_NEW event for warehouse {warehouse_data.id}")
        except Exception as e:
            logger.error(f"Failed to send WAREHOUSE_NEW event: {e}")

    def send_item_new(self, item_data):
        """Send ITEM_NEW event to the algorithm"""
        try:
            # Convert weight from kg (float) to grams (int) for C struct
            mass_grams = int((item_data.weight_kg or 0.0) * 1000)
            algo_item = AlgoItem(
                id=item_data.id,
                mass=mass_grams,
                name=item_data.name,
            )
            new_event(EventType.EVENT_ITEM_NEW, algo_item)
            logger.info(f"Sent ITEM_NEW event for item {item_data.id}")
        except Exception as e:
            logger.error(f"Failed to send ITEM_NEW event: {e}")

    def send_drone_remove(self, drone_id):
        """Send DRONE_REMOVE event to the algorithm"""
        try:
            id_hash = hash(drone_id) % (2**32)
            new_event(EventType.EVENT_DRONE_REMOVE, id_hash)
            logger.info(f"Sent DRONE_REMOVE event for {drone_id}")
        except Exception as e:
            logger.error(f"Failed to send DRONE_REMOVE event: {e}")

    def send_delivery_remove(self, delivery_id):
        """Send DELIVERY_REMOVE event to the algorithm"""
        try:
            new_event(EventType.EVENT_DELIVERY_REMOVE, delivery_id)
            logger.info(f"Sent DELIVERY_REMOVE event for delivery {delivery_id}")
        except Exception as e:
            logger.error(f"Failed to send DELIVERY_REMOVE event: {e}")

    def send_warehouse_remove(self, warehouse_id):
        """Send WAREHOUSE_REMOVE event to the algorithm"""
        try:
            new_event(EventType.EVENT_WAREHOUSE_REMOVE, warehouse_id)
            logger.info(f"Sent WAREHOUSE_REMOVE event for warehouse {warehouse_id}")
        except Exception as e:
            logger.error(f"Failed to send WAREHOUSE_REMOVE event: {e}")

    def send_item_remove(self, item_id):
        """Send ITEM_REMOVE event to the algorithm"""
        try:
            new_event(EventType.EVENT_ITEM_REMOVE, item_id)
            logger.info(f"Sent ITEM_REMOVE event for item {item_id}")
        except Exception as e:
            logger.error(f"Failed to send ITEM_REMOVE event: {e}")

    def get_assignment(self):
        """Get assignment from the algorithm (blocks until ready)"""
        try:
            mission = get_assignment()
            logger.info(f"Received assignment: mission {mission.mission_id} for drone {mission.drone_id} with {len(mission.waypoints)} waypoints")
            return mission
        except Exception as e:
            logger.error(f"Failed to get assignment: {e}")
            return None


# Singleton instance
algo_service = AlgoService()
