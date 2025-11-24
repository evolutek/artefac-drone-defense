#!/usr/bin/env python3
"""
Simulation Control Server - Artefac Drone Defense

Flask REST API server for controlling Gazebo simulation dynamically:
- Spawn/despawn drones with multiple model types
- Create/delete exclusion zones
- Manage entrepôts (warehouses)
- Manage livraisons (deliveries)

Port: 8080 (dedicated server, separate from main backend on port 8000)
"""

import os
import sys
import threading

# Add simulation_control package to Python path
sys.path.insert(0, '/root')

from flask import Flask
from flask_cors import CORS

# Import route registration functions from each module
from simulation_control.drones.routes import register_drone_routes
from simulation_control.zones.routes import register_zone_routes
from simulation_control.entrepots.routes import register_entrepot_routes
from simulation_control.livraisons.routes import register_livraison_routes
from simulation_control.common.config_start import map_config


def create_app():
    """Create and configure Flask app with all routes"""
    app = Flask(__name__)

    # Enable CORS for all routes (allows mobile app/frontend to access API)
    CORS(app)

    # Register all routes
    print("Registering drone routes...")
    register_drone_routes(app)

    print("Registering zone routes...")
    register_zone_routes(app)

    print("Registering entrepôt routes...")
    register_entrepot_routes(app)

    print("Registering livraison routes...")
    register_livraison_routes(app)

    print("✓ All routes registered successfully!")

    return app


if __name__ == '__main__':
    # Create Flask app
    app = create_app()

    # Get port from environment variable (default: 8080)
    port = int(os.getenv('FLASK_PORT', 8080))

    print("=" * 60)
    print("  Simulation Control Server - Artefac Drone Defense")
    print("=" * 60)
    print(f"  Server running on: http://0.0.0.0:{port}")
    print("  API Endpoints:")
    print("    - GET  /health                 → Server health + active counts")
    print("    - GET  /models                 → Available drone models")
    print("    - GET  /drones/active          → List active drones")
    print("    - POST /drones/spawn           → Spawn drone")
    print("    - POST /drones/refresh         → Refresh drone list from Gazebo")
    print("    - DELETE /drones/<drone_num>   → Remove drone")
    print("    - POST /drones/batch-delete    → Remove multiple drones")
    print("    - GET  /zones                  → List active zones")
    print("    - POST /zones                  → Create zone")
    print("    - DELETE /zones/<zone_id>      → Delete zone")
    print("    - POST /zones/batch-delete     → Delete multiple zones")
    print("    - GET  /entrepots              → List active entrepôts")
    print("    - POST /entrepots              → Create entrepôt")
    print("    - DELETE /entrepots/<id>       → Delete entrepôt")
    print("    - POST /entrepots/batch-delete → Delete multiple entrepôts")
    print("=" * 60)

    def run_after_start():
        print(">> Initialisation map...")
        map_config()
        print("<< thread end")

    threading.Thread(target=run_after_start, daemon=True).start()
   
    # Run Flask server
    app.run(host='0.0.0.0', port=port, debug=False)

    
