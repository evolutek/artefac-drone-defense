"""Entrepôt REST API endpoints"""

from flask import Flask, jsonify, request

from .manager import (
    discover_active_entrepots_from_gazebo,
    find_next_entrepot_number,
    load_active_entrepots,
    spawn_entrepot,
    despawn_entrepot
)


def register_entrepot_routes(app: Flask):
    """Register all entrepôt-related routes with the Flask app"""

    @app.route('/entrepots', methods=['GET'])
    def get_entrepots():
        """Get list of active entrepôts (dynamically queried from Gazebo)"""
        print("Start Get")
        active_entrepots = discover_active_entrepots_from_gazebo()
        print(active_entrepots)
        entrepots_list = []
        for entrepot_id, metadata in active_entrepots.items():
            entrepots_list.append({
                'entrepot_id': entrepot_id,
                'name': metadata['entrepot_name'],
                'type': metadata.get('entrepot_type', 'general'),
                'position': metadata['position'],
                'created_at': metadata.get('spawned_at')
            })

        return jsonify({
            'entrepots': entrepots_list,
            'count': len(entrepots_list)
        })

    @app.route('/entrepots', methods=['POST'])
    def create_entrepot():
        """
        Create a new entrepôt
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
        entrepot_type = data.get('type', 'general')

        # Find next entrepôt number
        entrepot_num = find_next_entrepot_number()

        # Execute spawn
        result = spawn_entrepot(
            entrepot_num,
            data['name'],
            position['x'],
            position['y'],
            position['z'],
            entrepot_type
        )

        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code

    @app.route('/entrepots/<entrepot_id>', methods=['DELETE'])
    def delete_entrepot(entrepot_id: str):
        """Remove an entrepôt by entrepot_id"""
        active_entrepots = load_active_entrepots()

        if entrepot_id not in active_entrepots:
            return jsonify({
                'success': False,
                'message': f'Entrepôt {entrepot_id} not found (not active)'
            }), 404

        result = despawn_entrepot(entrepot_id)

        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code

    @app.route('/entrepots/batch-delete', methods=['POST'])
    def batch_delete_entrepots():
        """
        Remove multiple entrepôts at once
        Body: {
            "entrepot_ids": ["entrepot_1", "entrepot_2", ...]
        }
        Returns: {
            "success": bool,
            "message": str,
            "results": [{"entrepot_id": str, "success": bool, "message": str}, ...],
            "succeeded_count": int,
            "failed_count": int
        }
        """
        data = request.get_json()

        # Validate request
        if not data or 'entrepot_ids' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing required field: entrepot_ids'
            }), 400

        entrepot_ids = data['entrepot_ids']

        if not isinstance(entrepot_ids, list):
            return jsonify({
                'success': False,
                'message': 'entrepot_ids must be an array'
            }), 400

        if len(entrepot_ids) == 0:
            return jsonify({
                'success': False,
                'message': 'entrepot_ids cannot be empty'
            }), 400

        # Load active entrepôts
        active_entrepots = load_active_entrepots()

        # Execute deletions
        results = []
        succeeded_count = 0
        failed_count = 0

        for entrepot_id in entrepot_ids:
            if entrepot_id not in active_entrepots:
                results.append({
                    'entrepot_id': entrepot_id,
                    'success': False,
                    'message': f'Entrepôt {entrepot_id} not found (not active)'
                })
                failed_count += 1
            else:
                result = despawn_entrepot(entrepot_id)
                results.append({
                    'entrepot_id': entrepot_id,
                    'success': result['success'],
                    'message': result['message']
                })
                if result['success']:
                    succeeded_count += 1
                else:
                    failed_count += 1

        # Determine overall success
        all_succeeded = failed_count == 0
        overall_message = f'Deleted {succeeded_count}/{len(entrepot_ids)} entrepôt(s)'
        if failed_count > 0:
            overall_message += f' ({failed_count} failed)'

        return jsonify({
            'success': all_succeeded,
            'message': overall_message,
            'results': results,
            'succeeded_count': succeeded_count,
            'failed_count': failed_count
        }), 200
