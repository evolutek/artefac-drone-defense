"""Generic MQTT presence event publishing"""

import json
import time
import paho.mqtt.publish as publish

from ..config import MQTT_BROKER, MQTT_PORT


def generic_publish_presence(topic: str, entity_id: str, event: str, reason: str = None, metadata: dict = None):
    """
    Publish entity presence event to MQTT topic

    Args:
        topic: MQTT topic (e.g., "drones/presence", "zones/presence")
        entity_id: Entity identifier (e.g., "drone_1", "zone_1")
        event: Event type ("connected" or "disconnected")
        reason: Optional reason (e.g., "spawn", "despawn", "mavros_lost")
        metadata: Optional metadata dict to include in payload (e.g., zone_name, type, position)
    """
    payload = {
        'event': event,
        f'{topic.split("/")[0][:-1]}_id': entity_id,  # Extract entity type from topic (drones -> drone)
        'timestamp': int(time.time()),
    }

    if reason:
        payload['reason'] = reason

    # Merge metadata into payload if provided
    if metadata:
        payload.update(metadata)

    try:
        publish.single(
            topic,
            payload=json.dumps(payload),
            hostname=MQTT_BROKER,
            port=MQTT_PORT,
            qos=1
        )
        print(f"[MQTT] Published presence event: {event} for {entity_id} (reason: {reason})")
    except Exception as e:
        print(f"[MQTT] Error publishing presence event: {e}")
