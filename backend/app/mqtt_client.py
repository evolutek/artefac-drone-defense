"""
MQTT Client for communication with ROS2 bridge
Subscribes to drone telemetry and publishes commands
"""
import os
import json
import logging
import threading
from typing import Optional, Dict, Any
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    def __init__(self):
        self.broker_host = os.getenv("MQTT_BROKER_HOST", "mqtt")
        self.broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.client_id = "backend_mqtt_client"

        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.thread: Optional[threading.Thread] = None

        # Callbacks for telemetry updates (to be set by WebSocket manager)
        self.telemetry_callback = None
        self.state_callback = None
        self.command_result_callback = None
        self.drone_event_callback = None  # For drone lifecycle events (spawn/ready/removed)

        # Command result storage (for synchronous command waiting)
        self.command_results = {}  # {drone_id: {command: result}}

    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")

            # Subscribe to all drone telemetry, state, command result topics, and global presence events
            client.subscribe("drone/+/telemetry")
            client.subscribe("drone/+/state")
            client.subscribe("drone/+/command_result")
            client.subscribe("drones/presence")
            logger.info("Subscribed to drone topics (telemetry, state, command_result) and drones/presence")
        else:
            self.connected = False
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")

    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnect from MQTT broker, return code: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")

    def on_message(self, client, userdata, msg):
        """Callback when message received from MQTT"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())

            logger.info(f"Received MQTT message on {topic}: {payload}")

            # Handle global presence topic
            if topic == "drones/presence":
                self._handle_presence_event(payload)
                return

            # Parse topic to get drone_id
            # Format: drone/{drone_id}/telemetry or drone/{drone_id}/state or drone/{drone_id}/command_result
            parts = topic.split("/")
            if len(parts) != 3:
                logger.warning(f"Invalid topic format: {topic}")
                return

            drone_id = parts[1]
            message_type = parts[2]

            # Handle drone-specific messages
            if message_type == "telemetry":
                self._handle_telemetry(drone_id, payload)
            elif message_type == "state":
                self._handle_state(drone_id, payload)
            elif message_type == "command_result":
                self._handle_command_result(drone_id, payload)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON payload: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _handle_telemetry(self, drone_id: str, payload: Dict[str, Any]):
        """Handle telemetry message"""
        logger.debug(f"Telemetry from {drone_id}: {payload}")

        # Check if drone was initializing before update (for transition detection)
        from .drone_state_manager import drone_state_manager
        drone_before = drone_state_manager.get_drone(drone_id)
        was_initializing = drone_before and drone_before.get("status") == "initializing"

        # Update in-memory state (fast, no DB latency)
        drone_state_manager.update_telemetry(drone_id, payload)

        # If drone transitioned from initializing to connected, notify clients
        if was_initializing:
            drone_after = drone_state_manager.get_drone(drone_id)
            if drone_after and drone_after.get("status") == "connected":
                if self.drone_event_callback:
                    self.drone_event_callback(
                        event_type="drone_ready",
                        drone_id=drone_id,
                        data={"status": "connected", "message": "Drone telemetry operational"}
                    )
                logger.info(f"Notified clients that {drone_id} is ready (telemetry operational)")

        # Store telemetry history in database (async, for post-flight analysis)
        from .models.database import SessionLocal
        from . import crud

        db = SessionLocal()
        try:
            # Store telemetry history
            crud.create_telemetry(
                db,
                drone_id=drone_id,
                position_x=payload.get("position_x"),
                position_y=payload.get("position_y"),
                position_z=payload.get("position_z"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                altitude=payload.get("altitude"),
                velocity_x=payload.get("velocity_x"),
                velocity_y=payload.get("velocity_y"),
                velocity_z=payload.get("velocity_z"),
                orientation_x=payload.get("orientation_x"),
                orientation_y=payload.get("orientation_y"),
                orientation_z=payload.get("orientation_z"),
                orientation_w=payload.get("orientation_w"),
                battery_level=payload.get("battery"),
            )

            db.commit()
        except Exception as e:
            logger.error(f"Error storing telemetry history: {e}")
            db.rollback()
        finally:
            db.close()

        # Notify WebSocket clients
        if self.telemetry_callback:
            self.telemetry_callback(drone_id, payload)

    def _handle_state(self, drone_id: str, payload: Dict[str, Any]):
        """Handle state message"""
        logger.debug(f"State from {drone_id}: {payload}")

        # Update in-memory state (fast, no DB latency)
        from .drone_state_manager import drone_state_manager
        drone_state_manager.update_state(drone_id, payload)

        # Notify WebSocket clients
        if self.state_callback:
            self.state_callback(drone_id, payload)

    def _handle_command_result(self, drone_id: str, payload: Dict[str, Any]):
        """Handle command result message"""
        logger.info(f"Command result from {drone_id}: {payload}")

        command = payload.get("command")
        success = payload.get("success", False)
        message = payload.get("message", "")

        # Store result for synchronous waiting
        if drone_id not in self.command_results:
            self.command_results[drone_id] = {}

        self.command_results[drone_id][command] = {
            "success": success,
            "message": message,
            "timestamp": payload.get("timestamp")
        }

        # Notify WebSocket clients
        if self.command_result_callback:
            self.command_result_callback(drone_id, payload)

    def _handle_presence_event(self, payload: Dict[str, Any]):
        """
        Handle drone presence events from global drones/presence topic
        Events: connected, disconnected
        """
        event = payload.get("event")
        drone_id = payload.get("drone_id")
        reason = payload.get("reason", "unknown")

        if not event or not drone_id:
            logger.warning(f"Invalid presence event: missing event or drone_id: {payload}")
            return

        from .drone_state_manager import drone_state_manager

        if event == "connected":
            logger.info(f"Drone {drone_id} connected (reason: {reason})")

            # Register drone immediately with "initializing" status
            newly_registered = drone_state_manager.register_drone(drone_id, status="initializing")

            # ALWAYS notify WebSocket clients about presence events (even for reconnections)
            # This ensures the frontend is aware of all connection events
            if self.drone_event_callback:
                self.drone_event_callback(
                    event_type="drone_spawning",
                    drone_id=drone_id,
                    data={"status": "initializing", "reason": reason}
                )
                logger.info(f"Notified clients of {drone_id} connection (newly_registered={newly_registered})")

            if newly_registered:
                logger.info(f"Registered {drone_id} with status 'initializing'")
            else:
                logger.debug(f"Drone {drone_id} already existed, updated to 'initializing'")

        elif event == "disconnected":
            logger.info(f"Drone {drone_id} disconnected (reason: {reason})")

            # Immediately remove drone from state manager
            removed = drone_state_manager.remove_drone(drone_id)

            if removed:
                # Notify WebSocket clients that drone was removed
                if self.drone_event_callback:
                    self.drone_event_callback(
                        event_type="drone_removed",
                        drone_id=drone_id,
                        data={"reason": reason}
                    )
                logger.info(f"Removed {drone_id} from state manager and notified clients")
            else:
                logger.warning(f"Tried to remove {drone_id} but it was not in state manager")

        else:
            logger.warning(f"Unknown presence event type: {event} for {drone_id}")

    def wait_for_command_result(self, drone_id: str, command: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Wait for command result from drone
        Returns result dict or None if timeout
        """
        import time
        start_time = time.time()

        # Clear previous result if exists
        if drone_id in self.command_results and command in self.command_results[drone_id]:
            del self.command_results[drone_id][command]

        # Wait for result with timeout
        while time.time() - start_time < timeout:
            if drone_id in self.command_results and command in self.command_results[drone_id]:
                result = self.command_results[drone_id][command]
                # Clean up
                del self.command_results[drone_id][command]
                return result
            time.sleep(0.1)

        logger.warning(f"Timeout waiting for command result: {command} from {drone_id}")
        return None

    def start(self):
        """Start MQTT client in background thread"""
        if self.client:
            logger.warning("MQTT client already started")
            return

        logger.info(f"Starting MQTT client connecting to {self.broker_host}:{self.broker_port}")

        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            logger.info("MQTT client loop started")
        except Exception as e:
            logger.error(f"Failed to start MQTT client: {e}")
            self.client = None

    def stop(self):
        """Stop MQTT client"""
        if self.client:
            logger.info("Stopping MQTT client")
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
            self.connected = False

    def is_connected(self) -> bool:
        """Check if connected to MQTT broker"""
        return self.connected

    def publish_command(self, drone_id: str, command: str, params: Optional[Dict[str, Any]] = None):
        """
        Publish command to drone via MQTT
        Topic: drone/{drone_id}/command
        """
        if not self.connected:
            logger.error("Cannot publish command: MQTT client not connected")
            return False

        topic = f"drone/{drone_id}/command"
        payload = {
            "command": command,
            "timestamp": json.dumps({"$date": {"$numberLong": str(int(threading.current_thread().ident))}})  # Quick hack for timestamp
        }

        if params:
            payload["params"] = params

        try:
            result = self.client.publish(topic, json.dumps(payload), qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published command {command} to {topic}")
                return True
            else:
                logger.error(f"Failed to publish command to {topic}, rc: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing command: {e}")
            return False


# Global MQTT client instance
mqtt_client = MQTTClient()
