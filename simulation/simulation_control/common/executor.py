"""Generic spawn/despawn execution operations"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Union

from ..config import SCRIPTS_DIR
from .storage import generic_load_json, generic_save_json
from .mqtt import generic_publish_presence


def generic_spawn_entity(
    script_name: str,
    script_args: List[str],
    entity_id: str,
    metadata: Dict[str, Any],
    storage_file: Path,
    storage_key: Union[int, str],
    mqtt_topic: str,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Execute spawn bash script for any entity type

    Args:
        script_name: Name of bash script (e.g., "spawn_drone.sh")
        script_args: List of arguments to pass to script
        entity_id: Entity identifier for MQTT (e.g., "drone_1")
        metadata: Entity metadata to store in JSON
        storage_file: Path to JSON storage file
        storage_key: Key to use in JSON storage (int or str)
        mqtt_topic: MQTT topic for presence events (e.g., "drones/presence")
        timeout: Script timeout in seconds (default: 60)

    Returns:
        {'success': bool, 'message': str, 'entity_id': str, ...}
    """
    print(f"[Spawn {entity_id}] Launching {script_name} with args: {script_args}")

    script_path = SCRIPTS_DIR / script_name
    spawn_cmd = ["bash", str(script_path)] + script_args

    try:
        result = subprocess.run(
            spawn_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SCRIPTS_DIR)
        )

        if result.returncode != 0:
            print(f"[Spawn {entity_id}] ✗ Spawn failed")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return {
                'success': False,
                'message': f'Spawn failed: {result.stderr or result.stdout}'
            }

        print(f"[Spawn {entity_id}] ✓ Entity spawned successfully")

        # Store metadata
        active_entities = generic_load_json(storage_file, key_as_int=isinstance(storage_key, int))
        active_entities[storage_key] = metadata
        generic_save_json(storage_file, active_entities)

        # Publish MQTT presence event with metadata
        generic_publish_presence(mqtt_topic, entity_id, "connected", reason="spawn", metadata=metadata)

        return {
            'success': True,
            'message': f'Entity {entity_id} spawned successfully'
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': f'Spawn timeout (>{timeout}s)'}
    except FileNotFoundError:
        return {'success': False, 'message': f'{script_name} not found'}
    except Exception as e:
        return {'success': False, 'message': f'Spawn error: {str(e)}'}


def generic_despawn_entity(
    script_name: str,
    script_args: List[str],
    entity_id: str,
    storage_file: Path,
    storage_key: Union[int, str],
    mqtt_topic: str,
    timeout: int = 15
) -> Dict[str, Any]:
    """
    Execute despawn bash script for any entity type

    Args:
        script_name: Name of bash script (e.g., "despawn_drone.sh")
        script_args: List of arguments to pass to script
        entity_id: Entity identifier for MQTT (e.g., "drone_1")
        storage_file: Path to JSON storage file
        storage_key: Key to remove from JSON storage (int or str)
        mqtt_topic: MQTT topic for presence events (e.g., "drones/presence")
        timeout: Script timeout in seconds (default: 15)

    Returns:
        {'success': bool, 'message': str, 'entity_id': str}
    """
    script_path = SCRIPTS_DIR / script_name

    try:
        result = subprocess.run(
            ["bash", str(script_path)] + script_args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SCRIPTS_DIR)
        )

        if result.returncode == 0:
            # Remove from active entities
            active_entities = generic_load_json(storage_file, key_as_int=isinstance(storage_key, int))
            if storage_key in active_entities:
                del active_entities[storage_key]
                generic_save_json(storage_file, active_entities)

            # Publish MQTT presence event
            generic_publish_presence(mqtt_topic, entity_id, "disconnected", reason="despawn")

            return {
                'success': True,
                'message': f'Entity {entity_id} removed successfully',
                'entity_id': entity_id
            }
        else:
            return {
                'success': False,
                'message': f'Failed to remove entity: {result.stderr}',
                'entity_id': entity_id
            }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': f'Despawn timeout (>{timeout}s)', 'entity_id': entity_id}
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}', 'entity_id': entity_id}
