"""
In-memory state manager for deliveries (livraisons)
Manages static delivery markers (no continuous telemetry like drones)
Thread-safe for use with MQTT client running in background thread
"""
import threading
import logging
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class DeliveryStateManager:
    """
    Manages delivery state in memory

    Deliveries are static entities (no continuous updates like drones).
    State transitions: register (connected) → remove (despawned)
    Thread-safe for concurrent access from MQTT thread and API endpoints.
    """

    def __init__(self):
        """Initialize state manager"""
        self._deliveries: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        logger.info("DeliveryStateManager initialized")

    def register_delivery(self, livraison_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Register a new delivery in state manager (called when delivery spawn is detected)

        Args:
            livraison_id: Unique delivery identifier (e.g., "livraison_1")
            metadata: Delivery metadata from MQTT presence event
                      {livraison_name, type, position, spawned_at}

        Returns:
            True if delivery was newly registered, False if already exists
        """
        with self._lock:
            if livraison_id in self._deliveries:
                logger.debug(f"Delivery {livraison_id} already registered, skipping")
                return False

            self._deliveries[livraison_id] = {
                "livraison_id": livraison_id,
                "livraison_name": metadata.get("livraison_name"),
                "type": metadata.get("type"),  # medicaments, foods, ammo, equipements
                "position": metadata.get("position"),  # {x, y, z}
                "status": "connected",  # Deliveries are immediately active (no initialization phase)
                "spawned_at": metadata.get("spawned_at"),
                "last_update": datetime.utcnow(),
            }
            logger.info(f"Registered delivery {livraison_id} (name: {metadata.get('livraison_name')}, type: {metadata.get('type')})")
            return True

    def get_delivery(self, livraison_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current state for a specific delivery

        Args:
            livraison_id: Unique delivery identifier

        Returns:
            Delivery state dict or None if not found
        """
        with self._lock:
            return self._deliveries.get(livraison_id)

    def get_active_deliveries(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active deliveries

        Returns:
            Dictionary of {livraison_id: delivery_state} for all deliveries
        """
        with self._lock:
            return dict(self._deliveries)

    def remove_delivery(self, livraison_id: str) -> bool:
        """
        Explicitly remove a delivery from state manager
        Called when receiving MQTT removal notification

        Args:
            livraison_id: Unique delivery identifier

        Returns:
            True if delivery was removed, False if not found
        """
        with self._lock:
            if livraison_id in self._deliveries:
                del self._deliveries[livraison_id]
                logger.info(f"Removed delivery {livraison_id} from state manager")
                return True
            else:
                logger.warning(f"Cannot remove delivery {livraison_id}: not found in state manager")
                return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about state manager

        Returns:
            Stats dict with total deliveries
        """
        with self._lock:
            return {
                "total_deliveries": len(self._deliveries),
            }


# Global singleton instance
delivery_state_manager = DeliveryStateManager()
