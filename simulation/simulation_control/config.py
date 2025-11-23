"""Configuration constants and model loading for Simulation Control Server"""

import json
import os
from pathlib import Path

# ============================================================================
# Directory and File Paths
# ============================================================================

SCRIPTS_DIR = Path("/root")  # spawn_*.sh and despawn_*.sh location
MODELS_CONFIG_FILE = Path("/root/models_config.json")  # Drone models configuration

# Active entities JSON storage files
ACTIVE_DRONES_FILE = Path("/tmp/active_drones.json")
ACTIVE_ZONES_FILE = Path("/tmp/active_zones.json")
ACTIVE_ENTREPOTS_FILE = Path("/tmp/active_entrepots.json")
ACTIVE_LIVRAISON_FILE = Path("/tmp/active_livraison.json")

# ============================================================================
# Limits
# ============================================================================

MAX_DRONES = 10

# ============================================================================
# MQTT Configuration
# ============================================================================

MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))

# ============================================================================
# Model Configuration Loader
# ============================================================================

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


# Load models configuration at module import
MODELS_CONFIG = load_models_config()
