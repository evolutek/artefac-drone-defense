"""Drone entity management - business logic for drones"""

from datetime import datetime
from typing import Dict, Optional

from ..config import (
    ACTIVE_DRONES_FILE,
    MAX_DRONES,
    MODELS_CONFIG,
    SCRIPTS_DIR
)
from ..common.storage import generic_load_json, generic_save_json
from ..common.gazebo import generic_discover_from_gazebo
from ..common.executor import generic_spawn_entity, generic_despawn_entity


# ============================================================================
# Storage Operations
# ============================================================================

def load_active_drones() -> Dict[int, dict]:
    """Load active drones from JSON file. Returns dict {drone_num: metadata}"""
    return generic_load_json(ACTIVE_DRONES_FILE, key_as_int=True)


def save_active_drones(drones: Dict[int, dict]):
    """Save active drones to JSON file"""
    generic_save_json(ACTIVE_DRONES_FILE, drones)


# ============================================================================
# Gazebo Discovery
# ============================================================================

def discover_active_drones_from_gazebo() -> Dict[int, dict]:
    """
    Query Gazebo directly to get list of active drone models (x500_*).
    This is the source of truth - always reflects what's actually in the simulation.

    Merges with JSON metadata (position, timestamps) if available.

    Returns: Dict {drone_num: metadata} of all active drones in Gazebo
    """

    def drone_id_generator(match: str) -> tuple:
        """Generate drone metadata from regex match"""
        drone_num = int(match)
        return drone_num, {
            'drone_id': f'drone_{drone_num + 1}',
            'model_name': f'x500_{drone_num}',
            'position': None,  # Unknown for discovered drones
            'spawned_at': None,  # Unknown
            'discovered': True  # Flag to indicate auto-discovered
        }

    return generic_discover_from_gazebo(
        pattern=r'x500_(\d+)',
        entity_type='drone',
        storage_file=ACTIVE_DRONES_FILE,
        id_generator=drone_id_generator
    )


# ============================================================================
# Auto-numbering
# ============================================================================

def find_next_drone_number() -> Optional[int]:
    """Find the next available drone number (0-9). Returns None if all slots full."""
    active = load_active_drones()
    used_numbers = set(active.keys())
    for num in range(MAX_DRONES):
        if num not in used_numbers:
            return num
    return None


# ============================================================================
# Spawn/Despawn Operations
# ============================================================================

def spawn_drone(drone_num: int, x: Optional[float] = None,
                y: Optional[float] = None, z: Optional[float] = None,
                model: Optional[str] = None) -> dict:
    """
    Execute spawn_drone.sh (unified script) to spawn Gazebo model + PX4 + ROS2 components

    Args:
        drone_num: Drone number (0-9)
        x, y, z: Optional spawn position
        model: Optional model type (e.g., "gz_x500", "gz_x500_depth"). Defaults to gz_x500.

    Returns: {'success': bool, 'message': str, 'drone_id': str, 'drone_num': int}
    """
    drone_id = f"drone_{drone_num + 1}"

    # Validate and get model configuration
    if model is None:
        model = MODELS_CONFIG.get('default_model', 'gz_x500')

    if model not in MODELS_CONFIG['models']:
        return {
            'success': False,
            'message': f'Invalid model: {model}. Available models: {", ".join(MODELS_CONFIG["models"].keys())}',
            'drone_id': drone_id,
            'drone_num': drone_num
        }

    model_config = MODELS_CONFIG['models'][model]
    gazebo_model = model_config['gazebo_model']

    # Prepare spawn script arguments
    script_args = [str(drone_num)]

    # Add position if provided
    if x is not None and y is not None and z is not None:
        script_args.extend([str(x), str(y), str(z)])

    # Prepare metadata
    metadata = {
        'drone_id': drone_id,
        'model_name': f'{gazebo_model}_{drone_num}',
        'model_type': model,
        'gazebo_model': gazebo_model,
        'position': {'x': x, 'y': y, 'z': z} if x is not None else None,
        'spawned_at': datetime.now().isoformat(),
    }

    # Execute spawn using generic function
    result = generic_spawn_entity(
        script_name="spawn_drone.sh",
        script_args=script_args,
        entity_id=drone_id,
        metadata=metadata,
        storage_file=ACTIVE_DRONES_FILE,
        storage_key=drone_num,
        mqtt_topic="drones/presence",
        timeout=60
    )

    # Add drone-specific fields to result
    result['drone_id'] = drone_id
    result['drone_num'] = drone_num

    return result


def despawn_drone(drone_num: int) -> dict:
    """
    Execute despawn_drone.sh script

    Args:
        drone_num: Drone number (0-9)

    Returns: {'success': bool, 'message': str, 'drone_id': str}
    """
    drone_id = f"drone_{drone_num + 1}"

    result = generic_despawn_entity(
        script_name="despawn_drone.sh",
        script_args=[str(drone_num)],
        entity_id=drone_id,
        storage_file=ACTIVE_DRONES_FILE,
        storage_key=drone_num,
        mqtt_topic="drones/presence",
        timeout=15
    )

    return result
