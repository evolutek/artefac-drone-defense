"""Zone REST API endpoints"""

from flask import Flask, jsonify, request

from .manager import (
    discover_active_zones_from_gazebo,
    find_next_zone_number,
    load_active_zones,
    spawn_zone,
    despawn_zone
)


def register_zone_routes(app: Flask):
    """Register all zone-related routes with the Flask app"""

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
        result = spawn_zone(
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

        result = despawn_zone(zone_id)

        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code

    @app.route('/zones/batch-delete', methods=['POST'])
    def batch_delete_zones():
        """
        Remove multiple zones at once
        Body: {
            "zone_ids": ["zone_1", "zone_2", ...]
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
                result = despawn_zone(zone_id)
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
