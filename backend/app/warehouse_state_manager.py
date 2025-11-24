"""
In-memory state manager for warehouses (entrepôts)
Manages static warehouse markers (no continuous telemetry like drones)
Thread-safe for use with MQTT client running in background thread
"""
import threading
import logging
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class WarehouseStateManager:
    """
    Manages warehouse state in memory

    Warehouses are static entities (no continuous updates like drones).
    State transitions: register (connected) → remove (despawned)
    Thread-safe for concurrent access from MQTT thread and API endpoints.
    """

    def __init__(self):
        """Initialize state manager"""
        self._warehouses: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        logger.info("WarehouseStateManager initialized")

    def register_warehouse(self, entrepot_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Register a new warehouse in state manager (called when warehouse spawn is detected)

        Args:
            entrepot_id: Unique warehouse identifier (e.g., "entrepot_1")
            metadata: Warehouse metadata from MQTT presence event
                      {entrepot_name, entrepot_model_name, entrepot_type, position, spawned_at}

        Returns:
            True if warehouse was newly registered, False if already exists
        """
        with self._lock:
            if entrepot_id in self._warehouses:
                logger.debug(f"Warehouse {entrepot_id} already registered, skipping")
                return False

            self._warehouses[entrepot_id] = {
                "entrepot_id": entrepot_id,
                "entrepot_name": metadata.get("entrepot_name"),
                "entrepot_model_name": metadata.get("entrepot_model_name"),
                "entrepot_type": metadata.get("entrepot_type"),  # medicaments, foods, ammo, equipements
                "position": metadata.get("position"),  # {x, y, z}
                "status": "connected",  # Warehouses are immediately active (no initialization phase)
                "spawned_at": metadata.get("spawned_at"),
                "last_update": datetime.utcnow(),
            }
            logger.info(f"Registered warehouse {entrepot_id} (name: {metadata.get('entrepot_name')}, type: {metadata.get('entrepot_type')})")
            return True

    def get_warehouse(self, entrepot_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current state for a specific warehouse

        Args:
            entrepot_id: Unique warehouse identifier

        Returns:
            Warehouse state dict or None if not found
        """
        with self._lock:
            return self._warehouses.get(entrepot_id)

    def get_active_warehouses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active warehouses

        Returns:
            Dictionary of {entrepot_id: warehouse_state} for all warehouses
        """
        with self._lock:
            return dict(self._warehouses)

    def remove_warehouse(self, entrepot_id: str) -> bool:
        """
        Explicitly remove a warehouse from state manager
        Called when receiving MQTT removal notification

        Args:
            entrepot_id: Unique warehouse identifier

        Returns:
            True if warehouse was removed, False if not found
        """
        with self._lock:
            if entrepot_id in self._warehouses:
                del self._warehouses[entrepot_id]
                logger.info(f"Removed warehouse {entrepot_id} from state manager")
                return True
            else:
                logger.warning(f"Cannot remove warehouse {entrepot_id}: not found in state manager")
                return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about state manager

        Returns:
            Stats dict with total warehouses
        """
        with self._lock:
            return {
                "total_warehouses": len(self._warehouses),
            }


# Global singleton instance
warehouse_state_manager = WarehouseStateManager()
