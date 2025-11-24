"""livraison REST API endpoints"""

from flask import Flask, jsonify, request

from .manager import (
    discover_active_livraisons_from_gazebo,
    find_next_livraison_number,
    load_active_livraisons,
    spawn_livraison,
    despawn_livraison
)


def register_livraison_routes(app: Flask):
    """Register all livraison-related routes with the Flask app"""

    @app.route('/livraisons', methods=['GET'])
    def get_livraisons():
        """Get list of active livraisons (dynamically queried from Gazebo)"""
        active_livraisons = discover_active_livraisons_from_gazebo()

        livraisons_list = []
        for livraison_id, metadata in active_livraisons.items():
            livraisons_list.append({
                'livraison_id': livraison_id,
                'name': metadata['livraison_name'],
                'type': metadata.get('livraison_type', 'general'),
                'position': metadata['position'],
                'created_at': metadata.get('spawned_at')
            })

        return jsonify({
            'livraisons': livraisons_list,
            'count': len(livraisons_list)
        })

    @app.route('/livraisons', methods=['POST'])
    def create_livraison():
        """
        Create a new livraison
        Body: {
            "name": string,
            "type": string (optional, default: "general"),
            "position": {"x": float, "y": float, "z": float}
        }
        """
        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'position']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400

        # Validate position coordinates
        position = data['position']
        if not all(coord in position for coord in ['x', 'y', 'z']):
            return jsonify({
                'success': False,
                'message': 'Position must contain x, y, and z coordinates'
            }), 400

        # Get optional type field (default to 'general')
        livraison_type = data.get('type', 'general')

        # Find next livraison number
        livraison_num = find_next_livraison_number()

        # Execute spawn
        result = spawn_livraison(
            livraison_num,
            data['name'],
            position['x'],
            position['y'],
            position['z'],
            livraison_type
        )

        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code

    @app.route('/livraisons/<livraison_id>', methods=['DELETE'])
    def delete_livraison(livraison_id: str):
        """Remove an livraison by livraison_id"""
        active_livraisons = load_active_livraisons()

        if livraison_id not in active_livraisons:
            return jsonify({
                'success': False,
                'message': f'livraison {livraison_id} not found (not active)'
            }), 404

        result = despawn_livraison(livraison_id)

        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code

    @app.route('/livraisons/batch-delete', methods=['POST'])
    def batch_delete_livraisons():
        """
        Remove multiple livraisons at once
        Body: {
            "livraison_ids": ["livraison_1", "livraison_2", ...]
        }
        Returns: {
            "success": bool,
            "message": str,
            "results": [{"livraison_id": str, "success": bool, "message": str}, ...],
            "succeeded_count": int,
            "failed_count": int
        }
        """
        data = request.get_json()

        # Validate request
        if not data or 'livraison_ids' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing required field: livraison_ids'
            }), 400

        livraison_ids = data['livraison_ids']

        if not isinstance(livraison_ids, list):
            return jsonify({
                'success': False,
                'message': 'livraison_ids must be an array'
            }), 400

        if len(livraison_ids) == 0:
            return jsonify({
                'success': False,
                'message': 'livraison_ids cannot be empty'
            }), 400

        # Load active livraisons
        active_livraisons = load_active_livraisons()

        # Execute deletions
        results = []
        succeeded_count = 0
        failed_count = 0

        for livraison_id in livraison_ids:
            if livraison_id not in active_livraisons:
                results.append({
                    'livraison_id': livraison_id,
                    'success': False,
                    'message': f'livraison {livraison_id} not found (not active)'
                })
                failed_count += 1
            else:
                result = despawn_livraison(livraison_id)
                results.append({
                    'livraison_id': livraison_id,
                    'success': result['success'],
                    'message': result['message']
                })
                if result['success']:
                    succeeded_count += 1
                else:
                    failed_count += 1

        # Determine overall success
        all_succeeded = failed_count == 0
        overall_message = f'Deleted {succeeded_count}/{len(livraison_ids)} livraison(s)'
        if failed_count > 0:
            overall_message += f' ({failed_count} failed)'

        return jsonify({
            'success': all_succeeded,
            'message': overall_message,
            'results': results,
            'succeeded_count': succeeded_count,
            'failed_count': failed_count
        }), 200
