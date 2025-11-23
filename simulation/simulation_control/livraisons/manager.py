"""
Livraison entity management - INCOMPLETE AND BUGGY CODE (copied as-is from original)

WARNING: This code has known bugs and is incomplete:
- Missing load_active_livraison() function
- execute_spawn_livraison() uses undefined variables (drone_num, drone_id)
- execute_despawn_livraison() uses wrong script (despawn_drone.sh)
- Function name typo: save_active_livrasion() instead of save_active_livraison()
- No MQTT presence publishing
- No Gazebo discovery function
- No auto-numbering function

This code is kept as-is for future refactoring.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ..config import SCRIPTS_DIR, ACTIVE_LIVRAISON_FILE


# ============================================================================
# BUGGY CODE BELOW - Copied from original simulation_control_server.py
# Lines 687-814
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
    spawn_cmd = ["bash", str(spawn_script_path), str(drone_num)]  # BUG: drone_num undefined

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
        active_livraison = load_active_livraison()  # BUG: function doesn't exist
        active_livraison[livraison_num] = {
            'livraison_id': livraison_id,
            'livraison_name': f'livraison_{livraison_num}',
            'position': {'x': x, 'y': y, 'z': z} if x is not None else None,
            'spawned_at': datetime.now().isoformat(),
        }
        save_active_livraison(active_livraison)  # BUG: function name is save_active_livrasion()

        # Publish presence event to MQTT
        publish_drone_presence(drone_id, "connected", reason="spawn")  # BUG: drone_id undefined, wrong function

        return {
            'success': True,
            'message': f'livraison {livraison_id} spawned successfully',
            'livraison_id': livraison_id,
            'lovraison_num': livraison_num  # BUG: typo "lovraison"
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Spawn timeout (>60s)', 'drone_id': drone_id, 'drone_num': drone_num}  # BUG: undefined variables
    except FileNotFoundError:
        return {'success': False, 'message': 'spawn_drone.sh not found', 'drone_id': drone_id, 'drone_num': drone_num}  # BUG: undefined variables
    except Exception as e:
        return {'success': False, 'message': f'Spawn error: {str(e)}', 'drone_id': drone_id, 'drone_num': drone_num}  # BUG: undefined variables


def execute_despawn_livraison(drone_num: int) -> dict:  # BUG: parameter should be livraison_num
    """
    Execute despawn_drone.sh script
    Returns: {'success': bool, 'message': str, 'drone_id': str}
    """
    script_path = SCRIPTS_DIR / "despawn_drone.sh"  # BUG: should be despawn_livraison.sh
    drone_id = f"drone_{drone_num + 1}"  # BUG: should be livraison_id

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
            active_drones = load_active_drones()  # BUG: should be load_active_livraison()
            if drone_num in active_drones:
                del active_drones[drone_num]
                save_active_drones(active_drones)  # BUG: should be save_active_livraison()

            # Publish presence event to MQTT
            publish_drone_presence(drone_id, "disconnected", reason="despawn")  # BUG: should be publish_livraison_presence()

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


def save_active_livrasion(livraison: Dict[int, dict]):  # BUG: typo in function name
    """Save active drones to JSON file"""
    with open(ACTIVE_LIVRAISON_FILE, 'w') as f:
        import json
        json.dump(livraison, f, indent=2)


# MISSING: load_active_livraison() function
# MISSING: discover_active_livraisons_from_gazebo() function
# MISSING: find_next_livraison_number() function
# MISSING: publish_livraison_presence() function
