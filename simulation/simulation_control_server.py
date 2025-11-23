#!/usr/bin/env python3
"""
Simulation Control Server - Artefac Drone Defense
Provides REST API to control Gazebo simulation (spawn/despawn drones and zones)

This server runs inside the ros2_integration container and has direct access
to spawn_drone.sh, despawn_drone.sh scripts and Gazebo gz commands.

Port: 8080
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
import paho.mqtt.publish as publish

app = Flask(__name__)
CORS(app)  # Enable CORS for Expo app

# Configuration
SCRIPTS_DIR = Path("/root")  # spawn_drone.sh and despawn_drone.sh location
ACTIVE_DRONES_FILE = Path("/tmp/active_drones.json")
ACTIVE_ZONES_FILE = Path("/tmp/active_zones.json")
MODELS_CONFIG_FILE = Path("/root/models_config.json")  # Drone models configuration
MAX_DRONES = 10
MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))

# Load models configuration
def load_models_config() -> dict:
    """Load drone models configuration from JSON file"""
    try:
        with open(MODELS_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Failed to load models config: {e}")
        # Fallback to default model only
        return {
            "models": {
                "gz_x500": {
                    "gazebo_model": "x500",
                    "autostart_id": 4001,
                    "type": "multirotor",
                    "description": "Standard Quadcopter",
                    "details": "Basic x500 quadcopter"
                }
            },
            "default_model": "gz_x500"
        }

MODELS_CONFIG = load_models_config()


# ============================================================================
# MQTT Helper Functions
# ============================================================================

def publish_drone_presence(drone_id: str, event: str, reason: str = None):
    """
    Publish drone presence event to global MQTT topic drones/presence

    Args:
        drone_id: Drone identifier (e.g., "drone_1")
        event: Event type ("connected" or "disconnected")
        reason: Optional reason (e.g., "spawn", "despawn", "mavros_lost")
    """
    payload = {
        'event': event,
        'drone_id': drone_id,
        'timestamp': int(time.time()),
    }

    if reason:
        payload['reason'] = reason

    try:
        publish.single(
            "drones/presence",
            payload=json.dumps(payload),
            hostname=MQTT_BROKER,
            port=MQTT_PORT,
            qos=1
        )
        print(f"[MQTT] Published presence event: {event} for {drone_id} (reason: {reason})")
    except Exception as e:
        print(f"[MQTT] Error publishing presence event: {e}")


# ============================================================================
# Helper Functions - Drone Management
# ============================================================================

def load_active_drones() -> Dict[int, dict]:
    """Load active drones from JSON file. Returns dict {drone_num: metadata}"""
    if not ACTIVE_DRONES_FILE.exists():
        return {}
    try:
        with open(ACTIVE_DRONES_FILE, 'r') as f:
            return {int(k): v for k, v in json.load(f).items()}
    except (json.JSONDecodeError, ValueError):
        return {}


def save_active_drones(drones: Dict[int, dict]):
    """Save active drones to JSON file"""
    with open(ACTIVE_DRONES_FILE, 'w') as f:
        json.dump(drones, f, indent=2)


def discover_active_drones_from_gazebo() -> Dict[int, dict]:
    """
    Query Gazebo directly to get list of active drone models (x500_*).
    This is the source of truth - always reflects what's actually in the simulation.

    Merges with JSON metadata (position, timestamps) if available.

    Returns: Dict {drone_num: metadata} of all active drones in Gazebo
    """
    discovered = {}

    try:
        # Query Gazebo for all models
        result = subprocess.run(
            ["gz", "model", "--list"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Parse output to find x500_* models
            # Example output:
            # Requesting state for world [default]...
            #
            # Available models:
            #     - ground_plane
            #     - x500_0
            #     - x500_1
            pattern = re.compile(r'^\s*-\s*x500_(\d+)$', re.MULTILINE)
            matches = pattern.findall(result.stdout)

            for drone_num_str in matches:
                drone_num = int(drone_num_str)
                discovered[drone_num] = {
                    'drone_id': f'drone_{drone_num + 1}',
                    'model_name': f'x500_{drone_num}',
                    'position': None,  # Unknown for discovered drones
                    'spawned_at': None,  # Unknown
                    'discovered': True  # Flag to indicate auto-discovered
                }
        else:
            print(f"Warning: gz model --list failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("Warning: gz model --list timeout")
    except Exception as e:
        print(f"Warning: Gazebo discovery failed: {e}")

    # Load existing metadata from JSON
    existing = load_active_drones()

    # Merge: keep metadata from JSON for drones that exist in Gazebo
    merged = {}
    for drone_num, gazebo_data in discovered.items():
        if drone_num in existing:
            # Drone exists in both - use JSON metadata (more complete)
            merged[drone_num] = existing[drone_num]
        else:
            # Drone only in Gazebo - use discovered data
            merged[drone_num] = gazebo_data

    # Sync JSON with Gazebo reality (remove ghost entries)
    if merged != existing:
        save_active_drones(merged)
        print(f"Synchronized active_drones.json with Gazebo (removed {len(existing) - len(merged)} ghost entries)")

    return merged


def find_next_drone_number() -> Optional[int]:
    """Find the next available drone number (0-9). Returns None if all slots full."""
    active = load_active_drones()
    used_numbers = set(active.keys())
    for num in range(MAX_DRONES):
        if num not in used_numbers:
            return num
    return None


def execute_spawn_drone(drone_num: int, x: Optional[float] = None,
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

    # ========================================================================
    # Execute unified spawn_drone.sh script (Gazebo + PX4 + ROS2)
    # ========================================================================
    print(f"[Spawn {drone_id}] Launching drone with model {model} using unified spawn script...")

    spawn_script_path = SCRIPTS_DIR / "spawn_drone.sh"
    spawn_cmd = ["bash", str(spawn_script_path), str(drone_num)]

    # Add position if provided
    if x is not None and y is not None and z is not None:
        spawn_cmd.extend([str(x), str(y), str(z)])

    try:
        result = subprocess.run(
            spawn_cmd,
            capture_output=True,
            text=True,
            timeout=60,  # Unified script needs more time (Gazebo + PX4 + ROS2)
            cwd=str(SCRIPTS_DIR)
        )

        if result.returncode != 0:
            print(f"[Spawn {drone_id}] ✗ Spawn failed")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return {
                'success': False,
                'message': f'Spawn failed: {result.stderr or result.stdout}',
                'drone_id': drone_id,
                'drone_num': drone_num
            }

        print(f"[Spawn {drone_id}] ✓ Drone spawned successfully (Gazebo + PX4 + ROS2)")

        # ====================================================================
        # SUCCESS: All components spawned
        # ====================================================================

        # Store drone metadata
        active_drones = load_active_drones()
        active_drones[drone_num] = {
            'drone_id': drone_id,
            'model_name': f'{gazebo_model}_{drone_num}',
            'model_type': model,
            'gazebo_model': gazebo_model,
            'position': {'x': x, 'y': y, 'z': z} if x is not None else None,
            'spawned_at': datetime.now().isoformat(),
        }
        save_active_drones(active_drones)

        # Publish presence event to MQTT
        publish_drone_presence(drone_id, "connected", reason="spawn")

        return {
            'success': True,
            'message': f'Drone {drone_id} spawned successfully (PX4 + ROS2)',
            'drone_id': drone_id,
            'drone_num': drone_num
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Spawn timeout (>60s)', 'drone_id': drone_id, 'drone_num': drone_num}
    except FileNotFoundError:
        return {'success': False, 'message': 'spawn_drone.sh not found', 'drone_id': drone_id, 'drone_num': drone_num}
    except Exception as e:
        return {'success': False, 'message': f'Spawn error: {str(e)}', 'drone_id': drone_id, 'drone_num': drone_num}


def execute_spawn_zone(zone_num: int, name: str, x: Optional[float] = None,
                       y: Optional[float] = None, z: Optional[float] = None,
                       radius: Optional[float] = None, type: str="jamming", A: Optional[float] = None) -> dict:
    """
    Execute spawn_drone.sh (unified script) to spawn Gazebo model + PX4 + ROS2 components

    Args:
        drone_num: Drone number (0-9)
        x, y, z: Optional spawn position
        radius: Radius of the sphere
        R,G,B,A : color and transparence of the sphere (0-1)

    Returns: {'success': bool, 'message': str, 'drone_id': str, 'drone_num': int}
    """
    zone_id = f"zone_{zone_num + 1}"
    type = type.lower()
    R = 0
    G = 0
    B = 0
    if (type == "jamming"):
        R=1
        G=0
        B=0
    elif (type == "no-fly"):
        R=1
        G=0.4
        B=0
    elif (type == "restricted"):
        R=1
        G=1
        B=0
    else:
        raise Exception("Invalid Argument: type must be jamming, no-fly, restricted")


    # ========================================================================
    # Execute unified spawn_zone.sh script (Gazebo)
    # ========================================================================
    print(f"[Spawn {zone_id}] Launching zone using unified spawn script...")

    spawn_script_path = SCRIPTS_DIR / "spawn_zone.sh"
    # spawn_zone.sh <zone_num> <name> <x> <y> <z> <radius> <R> <G> <B> <A>
    spawn_cmd = [
        "bash", str(spawn_script_path),
        str(zone_num),
        name,  # Zone name
        str(x) if x is not None else "5",
        str(y) if y is not None else "5",
        str(z) if z is not None else "0",
        str(radius) if radius is not None else "1",
        str(R),
        str(G),
        str(B),
        str(A) if A is not None else "0.75"
    ]
    try:
        result = subprocess.run(
            spawn_cmd,
            capture_output=True,
            text=True,
            timeout=60,  # Unified script needs more time (Gazebo + PX4 + ROS2)
            cwd=str(SCRIPTS_DIR)
        )

        if result.returncode != 0:
            print(f"[Spawn {zone_id}] ✗ Spawn failed")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return {
                'success': False,
                'message': f'Spawn failed: {result.stderr or result.stdout}',
                'zone_id': zone_id,
                'zone_num': zone_num
            }

        print(f"[Spawn {zone_id}] ✓ Zone spawned successfully (Gazebo)")

        # ====================================================================
        # SUCCESS: All components spawned
        # ====================================================================

        # Normalize zone name for Gazebo model (same logic as bash script)
        normalized_name = name.lower().replace(' ', '_')
        # Remove non-alphanumeric characters except underscore
        normalized_name = ''.join(c for c in normalized_name if c.isalnum() or c == '_')
        zone_model_name = f"zone_{normalized_name}"

        # Store zone metadata
        active_zones = load_active_zones()
        active_zones[zone_id] = {
            'zone_id': zone_id,
            'zone_name': name,
            'zone_model_name': zone_model_name,  # Gazebo model name for discovery
            'type': type,
            'position': {'x': x, 'y': y, 'z': z} if x is not None else None,
            'radius': radius,
            'spawned_at': datetime.now().isoformat(),
        }
        save_active_zones(active_zones)

        # Publish presence event to MQTT
        publish_zone_presence(zone_id, "connected", reason="spawn")

        return {
            'success': True,
            'message': f'Zone {zone_id} spawned successfully',
            'zone_id': zone_id,
            'zone_num': zone_num
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Spawn timeout (>60s)', 'zone_id': zone_id, 'zone_num': zone_num}
    except FileNotFoundError:
        return {'success': False, 'message': 'spawn_zone.sh not found', 'zone_id': zone_id, 'zone_num': zone_num}
    except Exception as e:
        return {'success': False, 'message': f'Spawn error: {str(e)}', 'zone_id': zone_id, 'zone_num': zone_num}

def publish_zone_presence(zone_id: str, event: str, reason: str = None):
    """
    Publish drone presence event to global MQTT topic drones/presence

    Args:
        drone_id: Drone identifier (e.g., "drone_1")
        event: Event type ("connected" or "disconnected")
        reason: Optional reason (e.g., "spawn", "despawn", "mavros_lost")
    """
    payload = {
        'event': event,
        'zone_id': zone_id,
        'timestamp': int(time.time()),
    }

    if reason:
        payload['reason'] = reason

    try:
        publish.single(
            "zones/presence",
            payload=json.dumps(payload),
            hostname=MQTT_BROKER,
            port=MQTT_PORT,
            qos=1
        )
        print(f"[MQTT] Published presence event: {event} for {zone_id} (reason: {reason})")
    except Exception as e:
        print(f"[MQTT] Error publishing presence event: {e}")

def execute_despawn_drone(drone_num: int) -> dict:
    """
    Execute despawn_drone.sh script
    Returns: {'success': bool, 'message': str, 'drone_id': str}
    """
    script_path = SCRIPTS_DIR / "despawn_drone.sh"
    drone_id = f"drone_{drone_num + 1}"

    try:
        result = subprocess.run(
            ["bash", str(script_path), str(drone_num)],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(SCRIPTS_DIR)
        )

        if result.returncode == 0:
            # Remove from active drones
            active_drones = load_active_drones()
            if drone_num in active_drones:
                del active_drones[drone_num]
                save_active_drones(active_drones)

            # Publish presence event to MQTT
            publish_drone_presence(drone_id, "disconnected", reason="despawn")

            return {
                'success': True,
                'message': f'Drone {drone_id} removed successfully',
                'drone_id': drone_id
            }
        else:
            return {
                'success': False,
                'message': f'Failed to remove drone: {result.stderr}',
                'drone_id': drone_id
            }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Despawn timeout (>15s)', 'drone_id': drone_id}
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}', 'drone_id': drone_id}


# ============================================================================
# Helper Functions - Zone Management
# ============================================================================

def load_active_zones() -> Dict[str, dict]:
    """Load active zones from JSON file. Returns dict {zone_id: metadata}"""
    if not ACTIVE_ZONES_FILE.exists():
        return {}
    try:
        with open(ACTIVE_ZONES_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_active_zones(zones: Dict[str, dict]):
    """Save active zones to JSON file"""
    with open(ACTIVE_ZONES_FILE, 'w') as f:
        json.dump(zones, f, indent=2)


def discover_active_zones_from_gazebo() -> Dict[str, dict]:
    """
    Query Gazebo directly to get list of active zone models (zone_*).
    This is the source of truth - always reflects what's actually in the simulation.

    Merges with JSON metadata (name, type, radius) if available.

    Returns: Dict {zone_id: metadata} of all active zones in Gazebo
    """
    discovered = {}

    try:
        # Query Gazebo for all models
        result = subprocess.run(
            ["gz", "model", "--list"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Parse output to find zone_* models
            # Example output:
            # Requesting state for world [default]...
            #
            # Available models:
            #     - ground_plane
            #     - zone_jamming_alpha
            #     - zone_no_fly_beta
            pattern = re.compile(r'^\s*-\s*(zone_\w+)$', re.MULTILINE)
            matches = pattern.findall(result.stdout)

            for zone_model_name in matches:
                # Try to find matching zone in existing JSON by model name
                zone_id = None
                existing = load_active_zones()

                for zid, zdata in existing.items():
                    if zdata.get('zone_model_name') == zone_model_name:
                        zone_id = zid
                        break

                # If not found in JSON, create a new ID
                if zone_id is None:
                    # Extract zone number from model name if possible
                    # Otherwise generate a unique ID
                    zone_id = f"discovered_{zone_model_name}"

                discovered[zone_id] = {
                    'zone_id': zone_id,
                    'zone_model_name': zone_model_name,
                    'zone_name': zone_model_name.replace('zone_', '').replace('_', ' ').title(),  # Pretty name
                    'type': 'unknown',     # Unknown type for discovered zones
                    'position': None,      # Unknown position
                    'radius': None,        # Unknown radius
                    'spawned_at': None,    # Unknown timestamp
                    'discovered': True     # Flag to indicate auto-discovered
                }
        else:
            print(f"Warning: gz model --list failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("Warning: gz model --list timeout")
    except Exception as e:
        print(f"Warning: Gazebo zone discovery failed: {e}")

    # Load existing metadata from JSON
    existing = load_active_zones()

    # Merge: keep metadata from JSON for zones that exist in Gazebo
    merged = {}
    for zone_id, gazebo_data in discovered.items():
        if zone_id in existing:
            # Zone exists in both - use JSON metadata (more complete)
            merged[zone_id] = existing[zone_id]
        else:
            # Zone only in Gazebo - use discovered data
            merged[zone_id] = gazebo_data

    # Sync JSON with Gazebo reality (remove ghost entries)
    # Only keep zones that were discovered in Gazebo
    discovered_model_names = {zdata['zone_model_name'] for zdata in discovered.values()}
    for zone_id, zone_data in existing.items():
        zone_model_name = zone_data.get('zone_model_name')
        if zone_model_name and zone_model_name in discovered_model_names and zone_id not in merged:
            # This zone's model exists in Gazebo but wasn't matched yet - keep it
            merged[zone_id] = zone_data

    # Save merged list if changed
    if merged != existing:
        save_active_zones(merged)
        print(f"Synchronized active_zones.json with Gazebo (found {len(merged)} zone(s))")

    return merged


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


def find_next_zone_id() -> str:
    """Find next available zone ID (zone_1, zone_2, ...) - DEPRECATED, use find_next_zone_number()"""
    return f"zone_{find_next_zone_number() + 1}"


def execute_despawn_zone(zone_id: str) -> dict:
    """
    Execute despawn_zone.sh script
    Returns: {'success': bool, 'message': str, 'zone_id': str}
    """
    script_path = SCRIPTS_DIR / "despawn_zone.sh"

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
    zone_name = zone_data.get('zone_name', zone_id)

    try:
        # Use zone_model_name for Gazebo (e.g., "zone_jamming_alpha")
        result = subprocess.run(
            ["bash", str(script_path), zone_model_name],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(SCRIPTS_DIR)
        )

        if result.returncode == 0:
            # Remove from active zones
            del active_zones[zone_id]
            save_active_zones(active_zones)

            return {
                'success': True,
                'message': f'Zone {zone_name} removed successfully',
                'zone_id': zone_id
            }
        else:
            return {
                'success': False,
                'message': f'Failed to remove zone: {result.stderr}',
                'zone_id': zone_id
            }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Zone despawn timeout (>10s)', 'zone_id': zone_id}
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}', 'zone_id': zone_id}


# ============================================================================
# REST API Endpoints
# ============================================================================

def execute_spawn_livraison(livraison_num: int, x: Optional[float] = None,
                       y: Optional[float] = None, z: Optional[float] = None) -> dict:
    """
    Execute spawn_livraison.sh (unified script) to spawn Gazebo model + PX4 + ROS2 components

    Args:
        livraison_num: Livraison number (0-9)
        x, y, z: Optional spawn position

    Returns: {'success': bool, 'message': str, 'drone_id': str, 'drone_num': int}
    """
    livraison_id = f"livraison_{livraison_num + 1}"

   
    # ========================================================================
    # Execute unified spawn_drone.sh script (Gazebo + PX4 + ROS2)
    # ========================================================================
    print(f"[Spawn {livraison_id}] Launching livraison using unified spawn script...")

    spawn_script_path = SCRIPTS_DIR / "spawn_livraison.sh"
    spawn_cmd = ["bash", str(spawn_script_path), str(drone_num)]

    # Add position if provided
    if x is not None and y is not None and z is not None:
        spawn_cmd.extend([str(x), str(y), str(z)])

    try:
        result = subprocess.run(
            spawn_cmd,
            capture_output=True,
            text=True,
            timeout=60,  # Unified script needs more time (Gazebo + PX4 + ROS2)
            cwd=str(SCRIPTS_DIR)
        )

        if result.returncode != 0:
            print(f"[Spawn {livraison_id}] ✗ Spawn failed")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return {
                'success': False,
                'message': f'Spawn failed: {result.stderr or result.stdout}',
                'livraison_id': livraison_id,
                'livraison_num': livraison_num
            }

        print(f"[Spawn {livraison_id}] ✓ Drone spawned successfully (Gazebo)")

        # ====================================================================
        # SUCCESS: All components spawned
        # ====================================================================

        # Store drone metadata
        active_livraison = load_active_livraison()
        active_livraison[livraison_num] = {
            'livraison_id': livraison_id,
            'livraison_name': f'livraison_{livraison_num}',
            'position': {'x': x, 'y': y, 'z': z} if x is not None else None,
            'spawned_at': datetime.now().isoformat(),
        }
        save_active_livraison(active_livraison)

        # Publish presence event to MQTT
        publish_drone_presence(drone_id, "connected", reason="spawn")

        return {
            'success': True,
            'message': f'livraison {livraison_id} spawned successfully',
            'livraison_id': livraison_id,
            'lovraison_num': livraison_num
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Spawn timeout (>60s)', 'drone_id': drone_id, 'drone_num': drone_num}
    except FileNotFoundError:
        return {'success': False, 'message': 'spawn_drone.sh not found', 'drone_id': drone_id, 'drone_num': drone_num}
    except Exception as e:
        return {'success': False, 'message': f'Spawn error: {str(e)}', 'drone_id': drone_id, 'drone_num': drone_num}


def execute_despawn_livraison(drone_num: int) -> dict:
    """
    Execute despawn_drone.sh script
    Returns: {'success': bool, 'message': str, 'drone_id': str}
    """
    script_path = SCRIPTS_DIR / "despawn_drone.sh"
    drone_id = f"drone_{drone_num + 1}"

    try:
        result = subprocess.run(
            ["bash", str(script_path), str(drone_num)],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(SCRIPTS_DIR)
        )

        if result.returncode == 0:
            # Remove from active drones
            active_drones = load_active_drones()
            if drone_num in active_drones:
                del active_drones[drone_num]
                save_active_drones(active_drones)

            # Publish presence event to MQTT
            publish_drone_presence(drone_id, "disconnected", reason="despawn")

            return {
                'success': True,
                'message': f'Drone {drone_id} removed successfully',
                'drone_id': drone_id
            }
        else:
            return {
                'success': False,
                'message': f'Failed to remove drone: {result.stderr}',
                'drone_id': drone_id
            }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Despawn timeout (>15s)', 'drone_id': drone_id}
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}', 'drone_id': drone_id}

def save_active_livrasion(livraison: Dict[int, dict]):
    """Save active drones to JSON file"""
    with open(ACTIVE_LIVRAISON_FILE, 'w') as f:
        json.dump(livraison, f, indent=2)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    active_drones = discover_active_drones_from_gazebo()
    active_zones = load_active_zones()

    return jsonify({
        'status': 'healthy',
        'service': 'simulation-control',
        'active_drones_count': len(active_drones),
        'active_zones_count': len(active_zones),
        'max_drones': MAX_DRONES
    })


@app.route('/models', methods=['GET'])
def get_available_models():
    """
    Get list of available drone models
    Returns: {
        "models": [
            {
                "id": "gz_x500",
                "description": "Standard Quadcopter",
                "details": "Basic x500 quadcopter...",
                "type": "multirotor"
            },
            ...
        ],
        "default_model": "gz_x500"
    }
    """
    models_list = []
    for model_id, config in MODELS_CONFIG['models'].items():
        models_list.append({
            'id': model_id,
            'description': config['description'],
            'details': config['details'],
            'type': config['type']
        })

    return jsonify({
        'models': models_list,
        'default_model': MODELS_CONFIG.get('default_model', 'gz_x500')
    })


@app.route('/drones/active', methods=['GET'])
def get_active_drones():
    """Get list of active drones (dynamically queried from Gazebo)"""
    active_drones = discover_active_drones_from_gazebo()

    drones_list = []
    for drone_num, metadata in active_drones.items():
        drones_list.append({
            'drone_num': drone_num,
            'drone_id': metadata['drone_id'],
            'model_name': metadata['model_name'],
            'position': metadata.get('position'),
            'spawned_at': metadata.get('spawned_at')
        })

    return jsonify({
        'drones': drones_list,
        'count': len(drones_list)
    })


@app.route('/drones/refresh', methods=['POST'])
def refresh_drones():
    """
    Manually trigger ROS2 topic scan to discover active drones.
    Useful if drones were spawned after the server started.
    """
    try:
        print("Manual drone refresh triggered...")
        discovered_drones = discover_active_drones_from_gazebo()

        # Save to JSON (already done inside discover function)
        # save_active_drones(discovered_drones)

        drones_list = []
        for drone_num, metadata in discovered_drones.items():
            drones_list.append({
                'drone_num': drone_num,
                'drone_id': metadata['drone_id'],
                'model_name': metadata['model_name'],
                'position': metadata.get('position'),
                'spawned_at': metadata.get('spawned_at'),
                'discovered': metadata.get('discovered', False)
            })

        print(f"✓ Refresh complete: {len(drones_list)} active drone(s)")

        return jsonify({
            'success': True,
            'message': f'Discovered {len(drones_list)} active drone(s)',
            'drones': drones_list,
            'count': len(drones_list)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Refresh failed: {str(e)}'
        }), 500


@app.route('/drones/spawn', methods=['POST'])
def spawn_drone():
    """
    Spawn a new drone
    Body: {
        "x": float (optional),
        "y": float (optional),
        "z": float (optional),
        "model": string (optional, defaults to "gz_x500")
    }
    """
    data = request.get_json() or {}

    # Find next available drone number
    drone_num = find_next_drone_number()
    if drone_num is None:
        return jsonify({
            'success': False,
            'message': f'Maximum number of drones ({MAX_DRONES}) reached'
        }), 400

    # Get position (optional)
    x = data.get('x')
    y = data.get('y')
    z = data.get('z')

    # Get model (optional, defaults to gz_x500)
    model = data.get('model')

    # Validate position (if provided, all coordinates must be present)
    if any(coord is not None for coord in [x, y, z]):
        if not all(coord is not None for coord in [x, y, z]):
            return jsonify({
                'success': False,
                'message': 'If position is provided, x, y, and z must all be specified'
            }), 400

    # Execute spawn
    result = execute_spawn_drone(drone_num, x, y, z, model)

    status_code = 200 if result['success'] else 500
    return jsonify(result), status_code


@app.route('/drones/batch-delete', methods=['POST'])
def batch_despawn_drones():
    """
    Remove multiple drones at once
    Body: {
        "drone_nums": [0, 1, 2, ...]
    }
    Returns: {
        "success": bool,
        "message": str,
        "results": [{"drone_num": int, "success": bool, "message": str}, ...],
        "succeeded_count": int,
        "failed_count": int
    }
    """
    data = request.get_json()

    # Validate request
    if not data or 'drone_nums' not in data:
        return jsonify({
            'success': False,
            'message': 'Missing required field: drone_nums'
        }), 400

    drone_nums = data['drone_nums']

    if not isinstance(drone_nums, list):
        return jsonify({
            'success': False,
            'message': 'drone_nums must be an array'
        }), 400

    if len(drone_nums) == 0:
        return jsonify({
            'success': False,
            'message': 'drone_nums cannot be empty'
        }), 400

    # Load active drones
    active_drones = load_active_drones()

    # Execute deletions
    results = []
    succeeded_count = 0
    failed_count = 0

    for drone_num in drone_nums:
        if drone_num not in active_drones:
            results.append({
                'drone_num': drone_num,
                'success': False,
                'message': f'Drone {drone_num} not found (not active)'
            })
            failed_count += 1
        else:
            result = execute_despawn_drone(drone_num)
            results.append({
                'drone_num': drone_num,
                'success': result['success'],
                'message': result['message']
            })
            if result['success']:
                succeeded_count += 1
            else:
                failed_count += 1

    # Determine overall success
    all_succeeded = failed_count == 0
    overall_message = f'Deleted {succeeded_count}/{len(drone_nums)} drone(s)'
    if failed_count > 0:
        overall_message += f' ({failed_count} failed)'

    return jsonify({
        'success': all_succeeded,
        'message': overall_message,
        'results': results,
        'succeeded_count': succeeded_count,
        'failed_count': failed_count
    }), 200


@app.route('/drones/<int:drone_num>', methods=['DELETE'])
def despawn_drone(drone_num: int):
    """Remove a drone by drone_num (0, 1, 2, ...)"""
    active_drones = load_active_drones()

    if drone_num not in active_drones:
        return jsonify({
            'success': False,
            'message': f'Drone {drone_num} not found (not active)'
        }), 404

    result = execute_despawn_drone(drone_num)

    status_code = 200 if result['success'] else 500
    return jsonify(result), status_code


@app.route('/zones', methods=['GET'])
def get_zones():
    """Get list of active exclusion zones (dynamically queried from Gazebo)"""
    active_zones = discover_active_zones_from_gazebo()

    zones_list = []
    for zone_id, metadata in active_zones.items():
        zones_list.append({
            'zone_id': zone_id,
            'name': metadata['zone_name'],
            'type': metadata['type'],
            'center': metadata['position'],
            'radius': metadata['radius'],
            'created_at': metadata.get('spawned_at')
        })

    return jsonify({
        'zones': zones_list,
        'count': len(zones_list)
    })


@app.route('/zones', methods=['POST'])
def create_zone():
    """
    Create a new exclusion zone
    Body: {
        "name": string,
        "type": "jamming" | "no-fly" | "restricted",
        "center": {"x": float, "y": float, "z": float},
        "radius": float
    }
    """
    data = request.get_json()

    # Validate required fields
    required_fields = ['name', 'type', 'center', 'radius']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'message': f'Missing required field: {field}'
            }), 400

    # Validate center coordinates
    center = data['center']
    if not all(coord in center for coord in ['x', 'y', 'z']):
        return jsonify({
            'success': False,
            'message': 'Center must contain x, y, and z coordinates'
        }), 400

    # Validate type
    valid_types = ['jamming', 'no-fly', 'restricted']
    if data['type'] not in valid_types:
        return jsonify({
            'success': False,
            'message': f'Invalid type. Must be one of: {", ".join(valid_types)}'
        }), 400

    # Find next zone number
    zone_num = find_next_zone_number()

    # Execute spawn
    result = execute_spawn_zone(
        zone_num,
        data['name'],
        center['x'],
        center['y'],
        center['z'],
        data['radius'],
        data['type']
    )

    status_code = 200 if result['success'] else 500
    return jsonify(result), status_code


@app.route('/zones/<zone_id>', methods=['DELETE'])
def delete_zone(zone_id: str):
    """Remove an exclusion zone by zone_id"""
    active_zones = load_active_zones()

    if zone_id not in active_zones:
        return jsonify({
            'success': False,
            'message': f'Zone {zone_id} not found (not active)'
        }), 404

    result = execute_despawn_zone(zone_id)

    status_code = 200 if result['success'] else 500
    return jsonify(result), status_code


@app.route('/zones/batch-delete', methods=['POST'])
def batch_delete_zones():
    """
    Remove multiple zones at once
    Body: {
        "zone_ids": ["zone_0", "zone_1", ...]
    }
    Returns: {
        "success": bool,
        "message": str,
        "results": [{"zone_id": str, "success": bool, "message": str}, ...],
        "succeeded_count": int,
        "failed_count": int
    }
    """
    data = request.get_json()

    # Validate request
    if not data or 'zone_ids' not in data:
        return jsonify({
            'success': False,
            'message': 'Missing required field: zone_ids'
        }), 400

    zone_ids = data['zone_ids']

    if not isinstance(zone_ids, list):
        return jsonify({
            'success': False,
            'message': 'zone_ids must be an array'
        }), 400

    if len(zone_ids) == 0:
        return jsonify({
            'success': False,
            'message': 'zone_ids cannot be empty'
        }), 400

    # Load active zones
    active_zones = load_active_zones()

    # Execute deletions
    results = []
    succeeded_count = 0
    failed_count = 0

    for zone_id in zone_ids:
        if zone_id not in active_zones:
            results.append({
                'zone_id': zone_id,
                'success': False,
                'message': f'Zone {zone_id} not found (not active)'
            })
            failed_count += 1
        else:
            result = execute_despawn_zone(zone_id)
            results.append({
                'zone_id': zone_id,
                'success': result['success'],
                'message': result['message']
            })
            if result['success']:
                succeeded_count += 1
            else:
                failed_count += 1

    # Determine overall success
    all_succeeded = failed_count == 0
    overall_message = f'Deleted {succeeded_count}/{len(zone_ids)} zone(s)'
    if failed_count > 0:
        overall_message += f' ({failed_count} failed)'

    return jsonify({
        'success': all_succeeded,
        'message': overall_message,
        'results': results,
        'succeeded_count': succeeded_count,
        'failed_count': failed_count
    }), 200


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Simulation Control Server - Artefac Drone Defense")
    print("=" * 60)
    print(f"Scripts directory: {SCRIPTS_DIR}")
    print(f"Active drones file: {ACTIVE_DRONES_FILE}")
    print(f"Active zones file: {ACTIVE_ZONES_FILE}")
    print(f"Max drones: {MAX_DRONES}")
    print("=" * 60)

    # Initialize ROS2
    print("Initializing ROS2 context...")
    try:
        rclpy.init()
        print("✓ ROS2 initialized successfully")
    except Exception as e:
        print(f"✗ ROS2 initialization failed: {e}")
        print("  (Server will continue but auto-discovery disabled)")

    # Discover existing drones from Gazebo
    print("Scanning Gazebo for active drones...")
    discovered_drones = discover_active_drones_from_gazebo()
    if discovered_drones:
        print(f"✓ Discovered {len(discovered_drones)} active drone(s):")
        for drone_num, metadata in discovered_drones.items():
            drone_id = metadata['drone_id']
            is_discovered = metadata.get('discovered', False)
            source = "ROS2 auto-discovery" if is_discovered else "existing JSON"
            print(f"  - {drone_id} (drone_num={drone_num}) from {source}")

        # Save merged list to JSON
        save_active_drones(discovered_drones)
        print(f"✓ Updated {ACTIVE_DRONES_FILE}")
    else:
        print("  No active drones found")

    print("=" * 60)
    print("Starting server on port 8080...")
    print("=" * 60)

    try:
        app.run(host='0.0.0.0', port=8080, debug=False)
    finally:
        # Cleanup ROS2
        if rclpy.ok():
            rclpy.shutdown()
