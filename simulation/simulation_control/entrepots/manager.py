"""Entrepôt entity management - business logic for warehouses"""
import time
from datetime import datetime
from typing import Dict, Optional

from ..config import ACTIVE_ENTREPOTS_FILE, SCRIPTS_DIR
from ..common.storage import generic_load_json, generic_save_json
from ..common.gazebo import generic_discover_from_gazebo, get_height
from ..common.executor import generic_spawn_entity, generic_despawn_entity

# ============================================================================
# Storage Operations
# ============================================================================

def load_active_entrepots() -> Dict[str, dict]:
    """Load active entrepôts from JSON file. Returns dict {entrepot_id: metadata}"""
    return generic_load_json(ACTIVE_ENTREPOTS_FILE, key_as_int=False)


def save_active_entrepots(entrepots: Dict[str, dict]):
    """Save active entrepôts to JSON file"""
    generic_save_json(ACTIVE_ENTREPOTS_FILE, entrepots)


# ============================================================================
# Gazebo Discovery
# ============================================================================

def discover_active_entrepots_from_gazebo() -> Dict[str, dict]:
    """
    Query Gazebo directly to get list of active entrepôt models (entrepot_*).
    This is the source of truth - always reflects what's actually in the simulation.

    Merges with JSON metadata (name, position) if available.

    Returns: Dict {entrepot_id: metadata} of all active entrepôts in Gazebo
    """

    def entrepot_id_generator(match: str) -> tuple:
        """Generate entrepôt metadata from regex match"""
        entrepot_model_name = match

        # Try to find matching entrepôt in existing JSON by model name
        existing = generic_load_json(ACTIVE_ENTREPOTS_FILE)
        entrepot_id = None

        for eid, edata in existing.items():
            if edata.get('entrepot_model_name') == entrepot_model_name:
                entrepot_id = eid
                break

        # If not found in JSON, create a new ID
        if entrepot_id is None:
            entrepot_id = f"discovered_{entrepot_model_name}"

        return entrepot_id, {
            'entrepot_id': entrepot_id,
            'entrepot_model_name': entrepot_model_name,
            'entrepot_name': entrepot_model_name.replace('entrepot_', '').replace('_', ' ').title(),  # Pretty name
            'entrepot_type': 'general',  # Default type for discovered entrepots
            'position': None,      # Unknown position
            'spawned_at': None,    # Unknown timestamp
            'discovered': True     # Flag to indicate auto-discovered
        }

    discovered = generic_discover_from_gazebo(
        pattern=r'(entrepot_\w+)',
        entity_type='entrepot',
        storage_file=ACTIVE_ENTREPOTS_FILE,
        id_generator=entrepot_id_generator
    )

    # Additional sync logic: keep entrepôts by model name match
    existing = generic_load_json(ACTIVE_ENTREPOTS_FILE)
    discovered_model_names = {edata['entrepot_model_name'] for edata in discovered.values()}
    merged = dict(discovered)
    time.sleep(2)
    for entrepot_id, entrepot_data in existing.items():
        entrepot_model_name = entrepot_data.get('entrepot_model_name')
        if entrepot_model_name and entrepot_model_name in discovered_model_names and entrepot_id not in merged:
            # This entrepôt's model exists in Gazebo but wasn't matched yet - keep it
            merged[entrepot_id] = entrepot_data

    # Save merged list if changed
    if merged != existing:
        generic_save_json(ACTIVE_ENTREPOTS_FILE, merged)
        print(f"Synchronized {ACTIVE_ENTREPOTS_FILE.name} with Gazebo (found {len(merged)} entrepôt(s))")

    return merged


# ============================================================================
# Auto-numbering
# ============================================================================

def find_next_entrepot_number() -> int:
    """Find next available entrepôt number (0, 1, 2, ...)"""
    active = load_active_entrepots()
    used_numbers = set()

    for entrepot_id in active.keys():
        if entrepot_id.startswith('entrepot_'):
            try:
                num = int(entrepot_id.split('_')[1]) - 1  # entrepot_1 -> num 0
                used_numbers.add(num)
            except (IndexError, ValueError):
                pass

    next_num = 0
    while next_num in used_numbers:
        next_num += 1

    return next_num


# ============================================================================
# Spawn/Despawn Operations
# ============================================================================

def spawn_entrepot(entrepot_num: int, name: str, x: Optional[float] = None,
                   y: Optional[float] = None, z: Optional[float] = None, etype: str = "medecines") -> dict:
    """
    Execute spawn_entrepot.sh script to spawn Gazebo entrepôt model

    Args:
        entrepot_num: Entrepôt number (0, 1, 2, ...)
        name: Entrepôt display name
        x, y, z: Optional spawn position
        etype: Type of warehouse (medecines, ammunition, food, equipment, blood, or custom)

    Returns: {'success': bool, 'message': str, 'entrepot_id': str, 'entrepot_num': int}
    """
    entrepot_id = f"entrepot_{entrepot_num + 1}"
    etype = etype.lower()

    # Validate entrepot type
    valid_types = {'medecines', 'ammunition', 'food', 'equipment', 'blood'}
    if etype not in valid_types and etype != 'custom':
        return {
            'success': False,
            'message': f'Invalid entrepot type: {etype}. Must be one of: {", ".join(sorted(valid_types))} or custom',
            'entrepot_id': entrepot_id,
            'entrepot_num': entrepot_num
        }

    # Prepare spawn script arguments
    if x is None :
        x = 10
    if y is None :
        y = 10
    offset = 0.5
    z = get_height(x, y) + offset
    print(z)
    # spawn_entrepot.sh <entrepot_num> <name> <x> <y> <z>
    script_args = [
        str(entrepot_num),
        name,
        str(x) if x is not None else "0",
        str(y) if y is not None else "0",
        str(z) if z is not None else "0"
    ]

    # Normalize entrepôt name for Gazebo model
    normalized_name = name.lower().replace(' ', '_')
    # Remove non-alphanumeric characters except underscore
    normalized_name = ''.join(c for c in normalized_name if c.isalnum() or c == '_')
    entrepot_model_name = f"entrepot_{normalized_name}"

    # Prepare metadata
    metadata = {
        'entrepot_id': entrepot_id,
        'entrepot_name': name,
        'entrepot_type': etype,
        'entrepot_model_name': entrepot_model_name,  # Gazebo model name for discovery
        'position': {'x': x, 'y': y, 'z': z} if x is not None else None,
        'spawned_at': datetime.now().isoformat(),
    }

    # Execute spawn using generic function
    result = generic_spawn_entity(
        script_name="spawn_entrepot.sh",
        script_args=script_args,
        entity_id=entrepot_id,
        metadata=metadata,
        storage_file=ACTIVE_ENTREPOTS_FILE,
        storage_key=entrepot_id,
        mqtt_topic="entrepots/presence",
        timeout=60
    )

    # Add entrepôt-specific fields to result
    result['entrepot_id'] = entrepot_id
    result['entrepot_num'] = entrepot_num

    return result


def despawn_entrepot(entrepot_id: str) -> dict:
    """
    Execute despawn_entrepot.sh script

    Args:
        entrepot_id: Entrepôt identifier (e.g., "entrepot_1")

    Returns: {'success': bool, 'message': str, 'entrepot_id': str}
    """
    # Load entrepôt metadata to get Gazebo model name
    active_entrepots = load_active_entrepots()

    if entrepot_id not in active_entrepots:
        return {
            'success': False,
            'message': f'Entrepôt {entrepot_id} not found in active entrepôts',
            'entrepot_id': entrepot_id
        }

    entrepot_data = active_entrepots[entrepot_id]
    entrepot_model_name = entrepot_data.get('entrepot_model_name')

    # If entrepot_model_name is not available, fallback to generating it from entrepot_name
    if not entrepot_model_name:
        entrepot_name = entrepot_data.get('entrepot_name', entrepot_id)
        # Normalize name like spawn script does
        normalized_name = entrepot_name.lower().replace(' ', '_')
        normalized_name = ''.join(c for c in normalized_name if c.isalnum() or c == '_')
        entrepot_model_name = f"entrepot_{normalized_name}"
        print(f"[despawn_entrepot] Generated model name from entrepot_name: {entrepot_model_name}")

    print(f"[despawn_entrepot] Using model name: {entrepot_model_name}")

    # Use entrepot_model_name for Gazebo
    result = generic_despawn_entity(
        script_name="despawn_entrepot.sh",
        script_args=[entrepot_model_name],
        entity_id=entrepot_id,
        storage_file=ACTIVE_ENTREPOTS_FILE,
        storage_key=entrepot_id,
        mqtt_topic="entrepots/presence",
        timeout=10
    )

    return result
