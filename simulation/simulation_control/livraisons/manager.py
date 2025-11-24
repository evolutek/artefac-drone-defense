"""Livraison entity management - business logic for deliveries"""

from datetime import datetime
from typing import Dict, Optional

from ..config import ACTIVE_LIVRAISON_FILE, SCRIPTS_DIR
from ..common.storage import generic_load_json, generic_save_json
from ..common.gazebo import generic_discover_from_gazebo
from ..common.executor import generic_spawn_entity, generic_despawn_entity


# ============================================================================
# Storage Operations
# ============================================================================

def load_active_livraisons() -> Dict[str, dict]:
    """Load active livraisons from JSON file. Returns dict {livraison_id: metadata}"""
    return generic_load_json(ACTIVE_LIVRAISON_FILE, key_as_int=False)


def save_active_livraisons(livraisons: Dict[str, dict]):
    """Save active livraisons to JSON file"""
    generic_save_json(ACTIVE_LIVRAISON_FILE, livraisons)


# ============================================================================
# Gazebo Discovery
# ============================================================================

def discover_active_livraisons_from_gazebo() -> Dict[str, dict]:
    """
    Query Gazebo directly to get list of active livraison models (livraison_*).
    This is the source of truth - always reflects what's actually in the simulation.

    Merges with JSON metadata (name, position) if available.

    Returns: Dict {livraison_id: metadata} of all active livraisons in Gazebo
    """

    def livraison_id_generator(match: str) -> tuple:
        """Generate livraison metadata from regex match"""
        livraison_model_name = match

        # Try to find matching livraison in existing JSON by model name
        existing = generic_load_json(ACTIVE_LIVRAISON_FILE)
        livraison_id = None

        for lid, ldata in existing.items():
            if ldata.get('livraison_model_name') == livraison_model_name:
                livraison_id = lid
                break

        # If not found in JSON, create a new ID
        if livraison_id is None:
            livraison_id = f"discovered_{livraison_model_name}"

        return livraison_id, {
            'livraison_id': livraison_id,
            'livraison_model_name': livraison_model_name,
            'livraison_name': livraison_model_name.replace('livraison_', '').replace('_', ' ').title(),  # Pretty name
            'position': None,      # Unknown position
            'spawned_at': None,    # Unknown timestamp
            'discovered': True     # Flag to indicate auto-discovered
        }

    discovered = generic_discover_from_gazebo(
        pattern=r'(livraison_\w+)',
        entity_type='livraison',
        storage_file=ACTIVE_LIVRAISON_FILE,
        id_generator=livraison_id_generator
    )

    # Additional sync logic: keep livraisons by model name match
    existing = generic_load_json(ACTIVE_LIVRAISON_FILE)
    discovered_model_names = {ldata['livraison_model_name'] for ldata in discovered.values()}
    merged = dict(discovered)

    for livraison_id, livraison_data in existing.items():
        livraison_model_name = livraison_data.get('livraison_model_name')
        if livraison_model_name and livraison_model_name in discovered_model_names and livraison_id not in merged:
            # This livraison's model exists in Gazebo but wasn't matched yet - keep it
            merged[livraison_id] = livraison_data

    # Save merged list if changed
    if merged != existing:
        generic_save_json(ACTIVE_LIVRAISON_FILE, merged)
        print(f"Synchronized {ACTIVE_LIVRAISON_FILE.name} with Gazebo (found {len(merged)} livraison(s))")

    return merged


# ============================================================================
# Auto-numbering
# ============================================================================

def find_next_livraison_number() -> int:
    """Find next available livraison number (0, 1, 2, ...)"""
    active = load_active_livraisons()
    used_numbers = set()

    for livraison_id in active.keys():
        if livraison_id.startswith('livraison_'):
            try:
                num = int(livraison_id.split('_')[1]) - 1  # livraison_1 -> num 0
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


def spawn_livraison(livraison_num: int, name: Optional[str] = None, x: Optional[float] = None,
               y: Optional[float] = None, z: Optional[float] = None, ltype: str= "medicament", ) -> dict:
    """
    Execute spawn_livraison.sh script to spawn Gazebo livraison marker

    Args:
        livraison_num: Livraison number (0, 1, 2, ...)
        x, y, z: Optional spawn position
    Returns: {'success': bool, 'message': str, 'livraison_id': str, 'livraison_num': int}
    """
    livraison_id = f"livraison_{livraison_num + 1}"
    ltype = ltype.lower()
    if ltype != "medicaments" and ltype != "foods" and ltype != "ammo" and ltype != "equipements":
         return {
            'success': False,
            'message': f'Invalid livraison type: {ltype}. Must be foods, medicaments, equipments or ammo',
            'livraison_id': livraison_id,
            'livraison_num': livraison_num
        }



    # Prepare spawn script arguments
    # spawn_livraison.sh <livraison_num> <name> <x> <y> <z> <radius> <R> <G> <B> <A>
    script_args = [
        str(livraison_num),
        name,
        str(x) if x is not None else "5",
        str(y) if y is not None else "5",
        str(z) if z is not None else "0",
    ]

    # Normalize livraison name for Gazebo model (same logic as bash script)
    normalized_name = name.lower().replace(' ', '_')
    # Remove non-alphanumeric characters except underscore
    normalized_name = ''.join(c for c in normalized_name if c.isalnum() or c == '_')
    livraison_model_name = f"livraison_{normalized_name}"

    # Prepare metadata
    metadata = {
        'livraison_id': livraison_id,
        'livraison_name': name,
        'position': {'x': x, 'y': y, 'z': z} if x is not None else None,
        'type': ltype,
        'spawned_at': datetime.now().isoformat(),
    }

    # Execute spawn using generic function
    result = generic_spawn_entity(
        script_name="spawn_livraison.sh",
        script_args=script_args,
        entity_id=livraison_id,
        metadata=metadata,
        storage_file=ACTIVE_LIVRAISON_FILE,
        storage_key=livraison_id,
        mqtt_topic="livraisons/presence",
        timeout=60
    )

    # Add livraison-specific fields to result
    result['livraison_id'] = livraison_id
    result['livraison_num'] = livraison_num

    return result


def despawn_livraison(id: str) -> dict:
    """
    Execute despawn_livraison.sh script

    Args:
        id: livraison identifier (e.g., "livraison_1")

    Returns: {'success': bool, 'message': str, 'livraison_id': str}
    """
    # Load livraison metadata to get Gazebo model name
    active_livraison = load_active_livraison()

    if id not in active_livraison:
        return {
            'success': False,
            'message': f'livraison {livraison_id} not found in active livraisons',
            'livraison_id': livraison_id
        }

    livraison_data = active_livraison[id]
    livraison_name = livraison_data.get('livraison_name', id)

    # Use livraison_model_name for Gazebo (e.g., "livraison_jamming_alpha")
    result = generic_despawn_entity(
        script_name="despawn_livraison.sh",
        script_args=[livraison_name],
        entity_id=livraison_id,
        storage_file=ACTIVE_LIVRAISON_FILE,
        storage_key=livraison_id,
        mqtt_topic="livraisons/presence",
        timeout=10
    )

    return result


def save_active_livrasion(livraison: Dict[int, dict]):  # BUG: typo in function name
    """Save active livraison to JSON file"""
    with open(ACTIVE_LIVRAISON_FILE, 'w') as f:
        import json
        json.dump(livraison, f, indent=2)


# MISSING: load_active_livraison() function
# MISSING: discover_active_livraisons_from_gazebo() function
# MISSING: find_next_livraison_number() function
# MISSING: publish_livraison_presence() function
