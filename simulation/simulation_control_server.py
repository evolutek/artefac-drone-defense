#!/usr/bin/env python3
"""
Simulation Control Server - Artefac Drone Defense
Provides REST API to control Gazebo simulation (spawn/despawn drones, zones, entrepôts, and livraisons)

This server runs inside the ros2_integration container and has direct access
to spawn/despawn bash scripts and Gazebo gz commands.

Port: 8080
"""

from flask import Flask
from flask_cors import CORS

# Import configuration
from simulation_control.config import (
    ACTIVE_DRONES_FILE,
    ACTIVE_ZONES_FILE,
    MAX_DRONES
)

# Import route registration functions
from simulation_control.drones.routes import register_drone_routes
from simulation_control.zones.routes import register_zone_routes
from simulation_control.entrepots.routes import register_entrepot_routes
from simulation_control.livraisons.routes import register_livraison_routes

# Import manager functions for initialization
from simulation_control.drones.manager import (
    discover_active_drones_from_gazebo,
    save_active_drones
)

# ============================================================================
# Flask Application Setup
# ============================================================================

app = Flask(__name__)
CORS(app)  # Enable CORS for Expo app

# Register all routes
register_drone_routes(app)
register_zone_routes(app)
register_entrepot_routes(app)
register_livraison_routes(app)

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Simulation Control Server - Artefac Drone Defense")
    print("=" * 60)
    print(f"Active drones file: {ACTIVE_DRONES_FILE}")
    print(f"Active zones file: {ACTIVE_ZONES_FILE}")
    print(f"Max drones: {MAX_DRONES}")
    print("=" * 60)

    # Initialize ROS2
    print("Initializing ROS2 context...")
    try:
        import rclpy
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
            source = "Gazebo auto-discovery" if is_discovered else "existing JSON"
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
        try:
            import rclpy
            if rclpy.ok():
                rclpy.shutdown()
        except:
            pass
