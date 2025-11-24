"""Zone entity management - business logic for exclusion zones"""

from datetime import datetime
from typing import Dict, Optional

from ..config import ACTIVE_ZONES_FILE, SCRIPTS_DIR
from ..common.storage import generic_load_json, generic_save_json
from ..common.gazebo import generic_discover_from_gazebo
from ..common.executor import generic_spawn_entity, generic_despawn_entity


# ============================================================================
# Storage Operations
# ============================================================================

def load_active_zones() -> Dict[str, dict]:
    """Load active zones from JSON file. Returns dict {zone_id: metadata}"""
    return generic_load_json(ACTIVE_ZONES_FILE, key_as_int=False)


def save_active_zones(zones: Dict[str, dict]):
    """Save active zones to JSON file"""
    generic_save_json(ACTIVE_ZONES_FILE, zones)


# ============================================================================
# Gazebo Discovery
# ============================================================================

def discover_active_zones_from_gazebo() -> Dict[str, dict]:
    """
    Query Gazebo directly to get list of active zone models (zone_*).
    This is the source of truth - always reflects what's actually in the simulation.

    Merges with JSON metadata (name, type, radius) if available.

    Returns: Dict {zone_id: metadata} of all active zones in Gazebo
    """

    def zone_id_generator(match: str) -> tuple:
        """Generate zone metadata from regex match"""
        zone_model_name = match

        # Try to find matching zone in existing JSON by model name
        existing = generic_load_json(ACTIVE_ZONES_FILE)
        zone_id = None

        for zid, zdata in existing.items():
            if zdata.get('zone_model_name') == zone_model_name:
                zone_id = zid
                break

        # If not found in JSON, create a new ID
        if zone_id is None:
            zone_id = f"discovered_{zone_model_name}"

        return zone_id, {
            'zone_id': zone_id,
            'zone_model_name': zone_model_name,
            'zone_name': zone_model_name.replace('zone_', '').replace('_', ' ').title(),  # Pretty name
            'type': 'unknown',     # Unknown type for discovered zones
            'position': None,      # Unknown position
            'radius': None,        # Unknown radius
            'spawned_at': None,    # Unknown timestamp
            'discovered': True     # Flag to indicate auto-discovered
        }

    discovered = generic_discover_from_gazebo(
        pattern=r'(zone_\w+)',
        entity_type='zone',
        storage_file=ACTIVE_ZONES_FILE,
        id_generator=zone_id_generator
    )

    # Additional sync logic specific to zones: keep zones by model name match
    existing = generic_load_json(ACTIVE_ZONES_FILE)
    discovered_model_names = {zdata['zone_model_name'] for zdata in discovered.values()}
    merged = dict(discovered)

    for zone_id, zone_data in existing.items():
        zone_model_name = zone_data.get('zone_model_name')
        if zone_model_name and zone_model_name in discovered_model_names and zone_id not in merged:
            # This zone's model exists in Gazebo but wasn't matched yet - keep it
            merged[zone_id] = zone_data

    # Save merged list if changed
    if merged != existing:
        generic_save_json(ACTIVE_ZONES_FILE, merged)
        print(f"Synchronized {ACTIVE_ZONES_FILE.name} with Gazebo (found {len(merged)} zone(s))")

    return merged


# ============================================================================
# Auto-numbering
# ============================================================================

def find_next_zone_number() -> int:
    """Find next available zone number (0, 1, 2, ...)"""
    active = load_active_zones()
    used_numbers = set()

    for zone_id in active.keys():
        if zone_id.startswith('zone_'):
            try:
                num = int(zone_id.split('_')[1]) - 1  # zone_1 -> num 0
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

def spawn_zone(zone_num: int, name: str, x: Optional[float] = None,
               y: Optional[float] = None, z: Optional[float] = None,
               radius: Optional[float] = None, zone_type: str = "jamming",
               A: Optional[float] = None) -> dict:
    """
    Execute spawn_zone.sh script to spawn Gazebo zone marker

    Args:
        zone_num: Zone number (0, 1, 2, ...)
        name: Zone display name
        x, y, z: Optional spawn position
        radius: Radius of the sphere
        zone_type: Type of zone ("jamming", "no-fly", "restricted")
        A: Transparency (0-1), defaults to 0.75

    Returns: {'success': bool, 'message': str, 'zone_id': str, 'zone_num': int}
    """
    print("start spawn zone")
    zone_id = f"zone_{zone_num + 1}"
    zone_type = zone_type.lower()

    # Calculate RGB color based on type
    R, G, B = 0, 0, 0
    if zone_type == "jamming":
        R, G, B = 1, 0, 0
    elif zone_type == "no-fly":
        R, G, B = 1, 0.4, 0
    elif zone_type == "restricted":
        R, G, B = 1, 1, 0
    else:
        return {
            'success': False,
            'message': f'Invalid zone type: {zone_type}. Must be jamming, no-fly, or restricted',
            'zone_id': zone_id,
            'zone_num': zone_num
        }

    # Prepare spawn script arguments
    # spawn_zone.sh <zone_num> <name> <x> <y> <z> <radius> <R> <G> <B> <A>
    script_args = [
        str(zone_num),
        name,
        str(x) if x is not None else "5",
        str(y) if y is not None else "5",
        str(z) if z is not None else "0",
        str(radius) if radius is not None else "1",
        str(R),
        str(G),
        str(B),
        str(A) if A is not None else "0.75"
    ]

    # Normalize zone name for Gazebo model (same logic as bash script)
    normalized_name = name.lower().replace(' ', '_')
    # Remove non-alphanumeric characters except underscore
    normalized_name = ''.join(c for c in normalized_name if c.isalnum() or c == '_')
    zone_model_name = f"zone_{normalized_name}"

    # Prepare metadata
    metadata = {
        'zone_id': zone_id,
        'zone_name': name,
        'zone_model_name': zone_model_name,  # Gazebo model name for discovery
        'type': zone_type,
        'position': {'x': x, 'y': y, 'z': z} if x is not None else None,
        'radius': radius,
        'spawned_at': datetime.now().isoformat(),
    }

    # Execute spawn using generic function
    result = generic_spawn_entity(
        script_name="spawn_zone.sh",
        script_args=script_args,
        entity_id=zone_id,
        metadata=metadata,
        storage_file=ACTIVE_ZONES_FILE,
        storage_key=zone_id,
        mqtt_topic="zones/presence",
        timeout=60
    )

    # Add zone-specific fields to result
    result['zone_id'] = zone_id
    result['zone_num'] = zone_num

    return result


def despawn_zone(zone_id: str) -> dict:
    """
    Execute despawn_zone.sh script

    Args:
        zone_id: Zone identifier (e.g., "zone_1")

    Returns: {'success': bool, 'message': str, 'zone_id': str}
    """
    # Load zone metadata to get Gazebo model name
    active_zones = load_active_zones()

    if zone_id not in active_zones:
        return {
            'success': False,
            'message': f'Zone {zone_id} not found in active zones',
            'zone_id': zone_id
        }

    zone_data = active_zones[zone_id]
    zone_model_name = zone_data.get('zone_model_name', zone_id)

    # Use zone_model_name for Gazebo (e.g., "zone_jamming_alpha")
    result = generic_despawn_entity(
        script_name="despawn_zone.sh",
        script_args=[zone_model_name],
        entity_id=zone_id,
        storage_file=ACTIVE_ZONES_FILE,
        storage_key=zone_id,
        mqtt_topic="zones/presence",
        timeout=10
    )

    return result
