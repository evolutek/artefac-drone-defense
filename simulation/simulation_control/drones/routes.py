"""Drone REST API endpoints"""

from flask import Flask, jsonify, request

from ..config import MAX_DRONES, MODELS_CONFIG
from .manager import (
    discover_active_drones_from_gazebo,
    find_next_drone_number,
    load_active_drones,
    spawn_drone,
    despawn_drone
)
from ..zones.manager import load_active_zones


def register_drone_routes(app: Flask):
    """Register all drone-related routes with the Flask app"""

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
        Manually trigger Gazebo scan to discover active drones.
        Useful if drones were spawned after the server started.
        """
        try:
            print("Manual drone refresh triggered...")
            discovered_drones = discover_active_drones_from_gazebo()

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
    def spawn_drone_endpoint():
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
        result = spawn_drone(drone_num, x, y, z, model)

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
                result = despawn_drone(drone_num)
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
    def despawn_drone_endpoint(drone_num: int):
        """Remove a drone by drone_num (0, 1, 2, ...)"""
        active_drones = load_active_drones()

        if drone_num not in active_drones:
            return jsonify({
                'success': False,
                'message': f'Drone {drone_num} not found (not active)'
            }), 404

        result = despawn_drone(drone_num)

        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code
