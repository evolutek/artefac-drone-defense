"""
In-memory state manager for drone fleet
Replaces database storage for ephemeral drone state (position, battery, armed status)
Thread-safe for use with MQTT client running in background thread
"""
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class DroneStateManager:
    """
    Manages ephemeral drone state in memory

    State is automatically cleaned up based on last_update timestamp (TTL pattern).
    Thread-safe for concurrent access from MQTT thread and API endpoints.
    """

    def __init__(self, default_timeout_seconds: int = 30):
        """
        Initialize state manager

        Args:
            default_timeout_seconds: Drones with no updates for this duration are considered inactive
        """
        self._drones: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._default_timeout = default_timeout_seconds
        logger.info(f"DroneStateManager initialized (timeout: {default_timeout_seconds}s)")

    def register_drone(self, drone_id: str, status: str = "initializing") -> bool:
        """
        Register a new drone in state manager (called when drone spawn is detected)

        Args:
            drone_id: Unique drone identifier (e.g., "drone_1")
            status: Initial status ("initializing" for spawning, "connected" for ready)

        Returns:
            True if drone was newly registered, False if already exists
        """
        with self._lock:
            if drone_id in self._drones:
                logger.debug(f"Drone {drone_id} already registered, skipping")
                return False

            self._drones[drone_id] = {
                "drone_id": drone_id,
                "status": status,
                "is_armed": False,
                "flight_mode": None,
                "mavros_connected": False,
                "created_at": datetime.utcnow(),
                "last_update": datetime.utcnow(),
            }
            logger.info(f"Registered drone {drone_id} with status '{status}'")
            return True

    def update_telemetry(self, drone_id: str, telemetry_data: Dict[str, Any]):
        """
        Update drone telemetry from MQTT message

        Args:
            drone_id: Unique drone identifier (e.g., "drone_1")
            telemetry_data: Telemetry payload from MQTT (position, velocity, battery, etc.)
        """
        with self._lock:
            if drone_id not in self._drones:
                self._drones[drone_id] = {
                    "drone_id": drone_id,
                    "status": "connected",
                    "is_armed": False,
                    "flight_mode": None,
                    "created_at": datetime.utcnow(),
                }
                logger.info(f"Auto-registered drone {drone_id} in state manager")

            # Transition from initializing to connected when first telemetry arrives
            if self._drones[drone_id].get("status") == "initializing":
                self._drones[drone_id]["status"] = "connected"
                logger.info(f"Drone {drone_id} transitioned from 'initializing' to 'connected' (telemetry ready)")

            # Update telemetry fields
            self._drones[drone_id].update({
                "position_x": telemetry_data.get("position_x"),
                "position_y": telemetry_data.get("position_y"),
                "position_z": telemetry_data.get("position_z"),
                "latitude": telemetry_data.get("latitude"),
                "longitude": telemetry_data.get("longitude"),
                "altitude": telemetry_data.get("altitude"),
                "velocity_x": telemetry_data.get("velocity_x"),
                "velocity_y": telemetry_data.get("velocity_y"),
                "velocity_z": telemetry_data.get("velocity_z"),
                "orientation_x": telemetry_data.get("orientation_x"),
                "orientation_y": telemetry_data.get("orientation_y"),
                "orientation_z": telemetry_data.get("orientation_z"),
                "orientation_w": telemetry_data.get("orientation_w"),
                "battery_level": telemetry_data.get("battery"),
                "last_update": datetime.utcnow(),
            })

            logger.debug(f"Updated telemetry for {drone_id}")

    def update_state(self, drone_id: str, state_data: Dict[str, Any]):
        """
        Update drone state from MQTT message

        Args:
            drone_id: Unique drone identifier
            state_data: State payload from MQTT (connected, armed, mode)
        """
        with self._lock:
            if drone_id not in self._drones:
                self._drones[drone_id] = {
                    "drone_id": drone_id,
                    "created_at": datetime.utcnow(),
                }
                logger.info(f"Auto-registered drone {drone_id} in state manager")

            # Determine status
            status = "connected" if state_data.get("connected") else "disconnected"
            if state_data.get("armed"):
                status = "armed"

            # Update state fields
            self._drones[drone_id].update({
                "status": status,
                "is_armed": state_data.get("armed", False),
                "flight_mode": state_data.get("mode"),
                "mavros_connected": state_data.get("connected", False),
                "last_update": datetime.utcnow(),
            })

            logger.debug(f"Updated state for {drone_id}: {status}, armed={state_data.get('armed')}")

    def get_drone(self, drone_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current state for a specific drone

        Args:
            drone_id: Unique drone identifier

        Returns:
            Drone state dict or None if not found
        """
        with self._lock:
            return self._drones.get(drone_id)

    def get_active_drones(self, timeout_seconds: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get all drones with recent heartbeat (active drones)

        Args:
            timeout_seconds: Override default timeout. Drones with last_update older than this are excluded.

        Returns:
            Dictionary of {drone_id: drone_state} for active drones only
        """
        timeout = timeout_seconds if timeout_seconds is not None else self._default_timeout
        cutoff_time = datetime.utcnow() - timedelta(seconds=timeout)

        with self._lock:
            active_drones = {
                drone_id: drone_data
                for drone_id, drone_data in self._drones.items()
                if drone_data.get("last_update") and drone_data["last_update"] > cutoff_time
            }

            logger.debug(f"get_active_drones: {len(active_drones)}/{len(self._drones)} drones active (timeout={timeout}s)")
            return active_drones

    def get_all_drones(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all drones regardless of activity status

        Returns:
            Dictionary of {drone_id: drone_state} for all drones
        """
        with self._lock:
            return dict(self._drones)

    def remove_drone(self, drone_id: str) -> bool:
        """
        Explicitly remove a drone from state manager
        Called when receiving MQTT removal notification or manual cleanup

        Args:
            drone_id: Unique drone identifier

        Returns:
            True if drone was removed, False if not found
        """
        with self._lock:
            if drone_id in self._drones:
                del self._drones[drone_id]
                logger.info(f"Removed drone {drone_id} from state manager")
                return True
            else:
                logger.warning(f"Cannot remove drone {drone_id}: not found in state manager")
                return False

    def cleanup_inactive_drones(self, timeout_seconds: Optional[int] = None):
        """
        Remove drones that haven't sent updates within timeout period
        Can be called periodically or manually

        Args:
            timeout_seconds: Override default timeout

        Returns:
            Number of drones removed
        """
        timeout = timeout_seconds if timeout_seconds is not None else self._default_timeout
        cutoff_time = datetime.utcnow() - timedelta(seconds=timeout)

        with self._lock:
            inactive_drones = [
                drone_id
                for drone_id, drone_data in self._drones.items()
                if not drone_data.get("last_update") or drone_data["last_update"] <= cutoff_time
            ]

            for drone_id in inactive_drones:
                del self._drones[drone_id]
                logger.info(f"Cleaned up inactive drone {drone_id}")

            if inactive_drones:
                logger.info(f"Cleanup: removed {len(inactive_drones)} inactive drones")

            return len(inactive_drones)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about state manager

        Returns:
            Stats dict with total drones, active drones, timeout config
        """
        active_drones = self.get_active_drones()

        with self._lock:
            return {
                "total_drones": len(self._drones),
                "active_drones": len(active_drones),
                "inactive_drones": len(self._drones) - len(active_drones),
                "timeout_seconds": self._default_timeout,
            }


# Global singleton instance
drone_state_manager = DroneStateManager(
    default_timeout_seconds=30  # TODO: Make configurable via env var
)
