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

    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")

            # Subscribe to all drone telemetry and state topics
            client.subscribe("drone/+/telemetry")
            client.subscribe("drone/+/state")
            logger.info("Subscribed to drone/+/telemetry and drone/+/state")
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

            logger.debug(f"Received MQTT message on {topic}: {payload}")

            # Parse topic to get drone_id
            # Format: drone/{drone_id}/telemetry or drone/{drone_id}/state
            parts = topic.split("/")
            if len(parts) != 3:
                logger.warning(f"Invalid topic format: {topic}")
                return

            drone_id = parts[1]
            message_type = parts[2]

            # Handle telemetry messages
            if message_type == "telemetry":
                self._handle_telemetry(drone_id, payload)
            elif message_type == "state":
                self._handle_state(drone_id, payload)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON payload: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _handle_telemetry(self, drone_id: str, payload: Dict[str, Any]):
        """Handle telemetry message"""
        logger.debug(f"Telemetry from {drone_id}: {payload}")

        # Import here to avoid circular dependency
        from .models.database import SessionLocal
        from . import crud

        # Update database with telemetry
        db = SessionLocal()
        try:
            # Check if drone exists, create if not
            drone = crud.get_drone(db, drone_id)
            if not drone:
                logger.info(f"Auto-registering drone {drone_id}")
                crud.create_drone(db, drone_id=drone_id)

            # Update drone with latest telemetry
            crud.update_drone_telemetry(
                db,
                drone_id=drone_id,
                position_x=payload.get("position_x"),
                position_y=payload.get("position_y"),
                position_z=payload.get("position_z"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                altitude=payload.get("altitude"),
                battery_level=payload.get("battery"),
            )

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
            logger.error(f"Error updating telemetry in database: {e}")
            db.rollback()
        finally:
            db.close()

        # Notify WebSocket clients
        if self.telemetry_callback:
            self.telemetry_callback(drone_id, payload)

    def _handle_state(self, drone_id: str, payload: Dict[str, Any]):
        """Handle state message"""
        logger.debug(f"State from {drone_id}: {payload}")

        # Import here to avoid circular dependency
        from .models.database import SessionLocal
        from . import crud

        # Update database with state
        db = SessionLocal()
        try:
            # Check if drone exists, create if not
            drone = crud.get_drone(db, drone_id)
            if not drone:
                logger.info(f"Auto-registering drone {drone_id}")
                crud.create_drone(db, drone_id=drone_id)

            # Update drone state
            status = "connected" if payload.get("connected") else "disconnected"
            if payload.get("armed"):
                status = "armed"

            crud.update_drone(
                db,
                drone_id=drone_id,
                is_armed=payload.get("armed", False),
                flight_mode=payload.get("mode"),
                status=status,
            )

            db.commit()
        except Exception as e:
            logger.error(f"Error updating state in database: {e}")
            db.rollback()
        finally:
            db.close()

        # Notify WebSocket clients
        if self.state_callback:
            self.state_callback(drone_id, payload)

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
