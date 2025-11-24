"""
WebSocket manager for real-time telemetry broadcasting
"""
import json
import logging
from typing import List, Dict, Optional, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        # Active connections for all telemetry
        self.active_connections: List[WebSocket] = []

        # Active connections per drone
        self.drone_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, drone_id: Optional[str] = None):
        """Accept new WebSocket connection"""
        await websocket.accept()

        if drone_id:
            # Connection for specific drone
            if drone_id not in self.drone_connections:
                self.drone_connections[drone_id] = []
            self.drone_connections[drone_id].append(websocket)
            logger.info(f"WebSocket client connected for drone {drone_id}")
        else:
            # Connection for all drones
            self.active_connections.append(websocket)
            logger.info("WebSocket client connected for all drones")

    def disconnect(self, websocket: WebSocket, drone_id: Optional[str] = None):
        """Remove WebSocket connection"""
        if drone_id:
            if drone_id in self.drone_connections:
                if websocket in self.drone_connections[drone_id]:
                    self.drone_connections[drone_id].remove(websocket)
                logger.info(f"WebSocket client disconnected from drone {drone_id}")
        else:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected from all drones")

    async def broadcast_telemetry(self, drone_id: str, telemetry: Dict[str, Any]):
        """
        Broadcast telemetry to all connected WebSocket clients
        """
        message = json.dumps({
            "type": "telemetry",
            "drone_id": drone_id,
            "data": telemetry,
        })

        # Broadcast to all connections
        await self._send_to_connections(self.active_connections, message)

        # Broadcast to drone-specific connections
        if drone_id in self.drone_connections:
            await self._send_to_connections(self.drone_connections[drone_id], message)

    async def broadcast_state(self, drone_id: str, state: Dict[str, Any]):
        """
        Broadcast state update to all connected WebSocket clients
        """
        message = json.dumps({
            "type": "state",
            "drone_id": drone_id,
            "data": state,
        })

        # Broadcast to all connections
        await self._send_to_connections(self.active_connections, message)

        # Broadcast to drone-specific connections
        if drone_id in self.drone_connections:
            await self._send_to_connections(self.drone_connections[drone_id], message)

    async def broadcast_drone_event(self, event_type: str, drone_id: str, data: Optional[Dict[str, Any]] = None):
        """
        Broadcast drone lifecycle events (spawning, ready, removed)

        Args:
            event_type: Event type ("drone_spawning", "drone_ready", "drone_removed")
            drone_id: Drone identifier
            data: Optional additional data (status, reason, etc.)
        """
        message = json.dumps({
            "type": event_type,
            "drone_id": drone_id,
            "data": data or {},
        })

        # Broadcast to all connections only (drone-specific connections may not exist yet)
        await self._send_to_connections(self.active_connections, message)
        logger.info(f"Broadcast {event_type} event for {drone_id}")

    async def broadcast_entity_event(self, entity_type: str, event_type: str, entity_id: str, data: Optional[Dict[str, Any]] = None):
        """
        Generic method to broadcast static entity lifecycle events (zones, warehouses, deliveries)

        Args:
            entity_type: Entity type ("zone", "warehouse", "delivery")
            event_type: Event type ("spawning", "removed")
            entity_id: Entity identifier (zone_id, entrepot_id, livraison_id)
            data: Optional additional data (status, reason, metadata, etc.)
        """
        message = json.dumps({
            "type": f"{entity_type}_{event_type}",
            "entity_id": entity_id,
            "entity_type": entity_type,
            "data": data or {},
        })

        # Broadcast to all connections
        await self._send_to_connections(self.active_connections, message)
        logger.info(f"Broadcast {entity_type}_{event_type} event for {entity_id}")

    async def _send_to_connections(self, connections: List[WebSocket], message: str):
        """Send message to list of connections, removing dead connections"""
        dead_connections = []

        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket client: {e}")
                dead_connections.append(connection)

        # Remove dead connections
        for connection in dead_connections:
            if connection in connections:
                connections.remove(connection)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# Register callbacks with MQTT client
def setup_mqtt_callbacks(event_loop):
    """
    Setup callbacks to link MQTT client with WebSocket manager
    Should be called after both are initialized with the main event loop

    Args:
        event_loop: The main asyncio event loop (from FastAPI)
    """
    from .mqtt_client import mqtt_client
    import asyncio

    def telemetry_callback(drone_id: str, payload: Dict[str, Any]):
        """Called when telemetry received from MQTT (runs in MQTT thread)"""
        try:
            # Schedule coroutine in the main event loop from MQTT thread
            asyncio.run_coroutine_threadsafe(
                websocket_manager.broadcast_telemetry(drone_id, payload),
                event_loop
            )
        except Exception as e:
            logger.error(f"Error broadcasting telemetry: {e}")

    def state_callback(drone_id: str, payload: Dict[str, Any]):
        """Called when state update received from MQTT (runs in MQTT thread)"""
        try:
            # Schedule coroutine in the main event loop from MQTT thread
            asyncio.run_coroutine_threadsafe(
                websocket_manager.broadcast_state(drone_id, payload),
                event_loop
            )
        except Exception as e:
            logger.error(f"Error broadcasting state: {e}")

    def drone_event_callback(event_type: str, drone_id: str, data: Dict[str, Any]):
        """Called when drone lifecycle event occurs (runs in MQTT thread)"""
        try:
            # Schedule coroutine in the main event loop from MQTT thread
            asyncio.run_coroutine_threadsafe(
                websocket_manager.broadcast_drone_event(event_type, drone_id, data),
                event_loop
            )
        except Exception as e:
            logger.error(f"Error broadcasting drone event: {e}")

    def zone_event_callback(event_type: str, entity_id: str, data: Dict[str, Any]):
        """Called when zone lifecycle event occurs (runs in MQTT thread)"""
        try:
            # Schedule coroutine in the main event loop from MQTT thread
            asyncio.run_coroutine_threadsafe(
                websocket_manager.broadcast_entity_event("zone", event_type, entity_id, data),
                event_loop
            )
        except Exception as e:
            logger.error(f"Error broadcasting zone event: {e}")

    def warehouse_event_callback(event_type: str, entity_id: str, data: Dict[str, Any]):
        """Called when warehouse lifecycle event occurs (runs in MQTT thread)"""
        try:
            # Schedule coroutine in the main event loop from MQTT thread
            asyncio.run_coroutine_threadsafe(
                websocket_manager.broadcast_entity_event("warehouse", event_type, entity_id, data),
                event_loop
            )
        except Exception as e:
            logger.error(f"Error broadcasting warehouse event: {e}")

    def delivery_event_callback(event_type: str, entity_id: str, data: Dict[str, Any]):
        """Called when delivery lifecycle event occurs (runs in MQTT thread)"""
        try:
            # Schedule coroutine in the main event loop from MQTT thread
            asyncio.run_coroutine_threadsafe(
                websocket_manager.broadcast_entity_event("delivery", event_type, entity_id, data),
                event_loop
            )
        except Exception as e:
            logger.error(f"Error broadcasting delivery event: {e}")

    mqtt_client.telemetry_callback = telemetry_callback
    mqtt_client.state_callback = state_callback
    mqtt_client.drone_event_callback = drone_event_callback
    mqtt_client.zone_event_callback = zone_event_callback
    mqtt_client.warehouse_event_callback = warehouse_event_callback
    mqtt_client.delivery_event_callback = delivery_event_callback
    logger.info("MQTT callbacks registered with WebSocket manager (drones, zones, warehouses, deliveries)")
