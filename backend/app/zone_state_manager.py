"""
In-memory state manager for exclusion zones
Manages static zone markers (no continuous telemetry like drones)
Thread-safe for use with MQTT client running in background thread
"""
import threading
import logging
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class ZoneStateManager:
    """
    Manages exclusion zone state in memory

    Zones are static entities (no continuous updates like drones).
    State transitions: register (connected) → remove (despawned)
    Thread-safe for concurrent access from MQTT thread and API endpoints.
    """

    def __init__(self):
        """Initialize state manager"""
        self._zones: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        logger.info("ZoneStateManager initialized")

    def register_zone(self, zone_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Register a new zone in state manager (called when zone spawn is detected)

        Args:
            zone_id: Unique zone identifier (e.g., "zone_1")
            metadata: Zone metadata from MQTT presence event
                      {zone_name, zone_model_name, type, position, radius, spawned_at}

        Returns:
            True if zone was newly registered, False if already exists
        """
        with self._lock:
            if zone_id in self._zones:
                logger.debug(f"Zone {zone_id} already registered, skipping")
                return False

            self._zones[zone_id] = {
                "zone_id": zone_id,
                "zone_name": metadata.get("zone_name"),
                "zone_model_name": metadata.get("zone_model_name"),
                "type": metadata.get("type"),  # jamming, no-fly, restricted
                "position": metadata.get("position"),  # {x, y, z}
                "radius": metadata.get("radius"),
                "status": "connected",  # Zones are immediately active (no initialization phase)
                "spawned_at": metadata.get("spawned_at"),
                "last_update": datetime.utcnow(),
            }
            logger.info(f"Registered zone {zone_id} (name: {metadata.get('zone_name')}, type: {metadata.get('type')})")
            return True

    def get_zone(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current state for a specific zone

        Args:
            zone_id: Unique zone identifier

        Returns:
            Zone state dict or None if not found
        """
        with self._lock:
            return self._zones.get(zone_id)

    def get_active_zones(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active zones

        Returns:
            Dictionary of {zone_id: zone_state} for all zones
        """
        with self._lock:
            return dict(self._zones)

    def remove_zone(self, zone_id: str) -> bool:
        """
        Explicitly remove a zone from state manager
        Called when receiving MQTT removal notification

        Args:
            zone_id: Unique zone identifier

        Returns:
            True if zone was removed, False if not found
        """
        with self._lock:
            if zone_id in self._zones:
                del self._zones[zone_id]
                logger.info(f"Removed zone {zone_id} from state manager")
                return True
            else:
                logger.warning(f"Cannot remove zone {zone_id}: not found in state manager")
                return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about state manager

        Returns:
            Stats dict with total zones
        """
        with self._lock:
            return {
                "total_zones": len(self._zones),
            }


# Global singleton instance
zone_state_manager = ZoneStateManager()
