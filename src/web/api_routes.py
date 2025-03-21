
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3

"""
API routes for the AMSLPR system.
"""

from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import json
import logging

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Global variables
db_manager = None
camera_manager = None
paxton_integration = None
nayax_integration = None


def init_api_routes(database_manager, cam_manager=None, paxton_integ=None, nayax_integ=None):
    """
    Initialize API routes with database manager and camera manager.
    
    Args:
        database_manager: Database manager instance
        cam_manager: Camera manager instance
        paxton_integ: Paxton integration instance
        nayax_integ: Nayax integration instance
    """
    global db_manager, camera_manager, paxton_integration, nayax_integration
    db_manager = database_manager
    camera_manager = cam_manager
    paxton_integration = paxton_integ
    nayax_integration = nayax_integ


# API key authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key is missing'}), 401
        
        # Check if API key is valid
        if not db_manager or not db_manager.validate_api_key(api_key):
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated


@api_bp.route('/vehicles', methods=['GET'])
@require_api_key
def get_vehicles():
    """
    Get list of vehicles.
    """
    if not db_manager:
        return jsonify({'error': 'Database manager not available'}), 500
    
    try:
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get vehicles
        vehicles = db_manager.get_vehicles(
            limit=limit,
            offset=offset
        )
        
        return jsonify({'vehicles': vehicles})
    except Exception as e:
        current_app.logger.error(f"API error getting vehicles: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/vehicles/<plate_number>', methods=['GET'])
@require_api_key
def get_vehicle(plate_number):
    """
    Get vehicle details.
    
    Args:
        plate_number (str): License plate number
    """
    if not db_manager:
        return jsonify({'error': 'Database manager not available'}), 500
    
    try:
        # Get vehicle
        vehicle = db_manager.get_vehicle(plate_number)
        
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        
        return jsonify({'vehicle': vehicle})
    except Exception as e:
        current_app.logger.error(f"API error getting vehicle {plate_number}: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/access-logs', methods=['GET'])
@require_api_key
def get_access_logs():
    """
    Get access logs.
    """
    if not db_manager:
        return jsonify({'error': 'Database manager not available'}), 500
    
    try:
        # Get query parameters
        plate_number = request.args.get('plate_number', '')
        start_time = request.args.get('start_time', '')
        end_time = request.args.get('end_time', '')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get access logs
        logs = db_manager.get_access_logs(
            plate_number=plate_number if plate_number else None,
            start_time=start_time if start_time else None,
            end_time=end_time if end_time else None,
            limit=limit,
            offset=offset
        )
        
        return jsonify({'access_logs': logs})
    except Exception as e:
        current_app.logger.error(f"API error getting access logs: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/camera/<camera_id>/settings', methods=['GET'])
@require_api_key
def get_camera_settings(camera_id):
    """
    Get camera settings.
    
    Args:
        camera_id (str): ID of the camera to get settings for
    """
    try:
        # Get camera manager
        from src.web.camera_routes import onvif_camera_manager
        if onvif_camera_manager is None:
            from src.web.camera_routes import init_camera_manager
            init_camera_manager(current_app.config)
        
        # Get camera
        cameras = onvif_camera_manager.get_cameras()
        if camera_id not in cameras:
            return jsonify({'success': False, 'error': 'Camera not found'})
        
        camera = cameras[camera_id]
        
        # Return camera settings
        return jsonify({
            'success': True,
            'camera': {
                'id': camera_id,
                'name': camera.get('name', ''),
                'ip': camera.get('ip', ''),
                'port': camera.get('port', ''),
                'username': camera.get('username', ''),
                'enabled': camera.get('enabled', True),
                'detection_area': camera.get('detection_area', None),
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error getting camera settings: {e}")
        return jsonify({'success': False, 'error': str(e)})


@api_bp.route('/camera/<camera_id>/test-connection', methods=['POST'])
@require_api_key
def test_camera_connection(camera_id):
    """
    Test connection to a camera.
    
    Args:
        camera_id (str): ID of the camera to test connection to
    """
    try:
        # Get camera manager
        from src.web.camera_routes import onvif_camera_manager
        if onvif_camera_manager is None:
            from src.web.camera_routes import init_camera_manager
            init_camera_manager(current_app.config)
        
        # Get camera
        cameras = onvif_camera_manager.get_cameras()
        if camera_id not in cameras:
            return jsonify({'success': False, 'error': 'Camera not found'})
        
        camera = cameras[camera_id]
        
        # Get credentials from form
        username = request.form.get('username', camera.get('username', ''))
        password = request.form.get('password', '')
        
        # If password is empty, use existing password
        if not password:
            password = camera.get('password', '')
        
        # Test connection
        result = onvif_camera_manager.test_connection(
            camera.get('ip', ''),
            camera.get('port', ''),
            username,
            password
        )
        
        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Connection failed'})
    except Exception as e:
        current_app.logger.error(f"Error testing camera connection: {e}")
        return jsonify({'success': False, 'error': str(e)})


@api_bp.route('/nayax/request-payment', methods=['POST'])
@require_api_key
def request_nayax_payment():
    """
    Request payment from Nayax terminal.
    
    Request body:
    {
        "amount": 10.50,
        "session_id": 123,
        "plate_number": "ABC123",
        "payment_location": "exit"  # Optional, defaults to "exit"
    }
    """
    if not nayax_integration:
        return jsonify({'error': 'Nayax integration not available'}), 500
    
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing request data'}), 400
        
        # Check required fields
        required_fields = ['amount', 'session_id', 'plate_number']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing {field} in request'}), 400
        
        # Get payment parameters
        amount = float(data['amount'])
        session_id = int(data['session_id'])
        plate_number = data['plate_number']
        payment_location = data.get('payment_location', 'exit')
        
        # Request payment from Nayax terminal
        result = nayax_integration.request_payment(
            amount=amount,
            session_id=session_id,
            plate_number=plate_number,
            payment_location=payment_location
        )
        
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"API error requesting Nayax payment: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/nayax/transaction-status', methods=['GET'])
@require_api_key
def get_nayax_transaction_status():
    """
    Get current Nayax transaction status.
    """
    if not nayax_integration:
        return jsonify({'error': 'Nayax integration not available'}), 500
    
    try:
        # Get current transaction status
        status = nayax_integration.get_current_transaction()
        
        return jsonify(status)
    except Exception as e:
        current_app.logger.error(f"API error getting Nayax transaction status: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/nayax/cancel-transaction', methods=['POST'])
@require_api_key
def cancel_nayax_transaction():
    """
    Cancel current Nayax transaction.
    """
    if not nayax_integration:
        return jsonify({'error': 'Nayax integration not available'}), 500
    
    try:
        # Cancel current transaction
        result = nayax_integration.cancel_current_transaction()
        
        return jsonify({
            'success': result,
            'message': 'Transaction cancelled' if result else 'Failed to cancel transaction'
        })
    except Exception as e:
        current_app.logger.error(f"API error cancelling Nayax transaction: {e}")
        return jsonify({'error': str(e)}), 500


def register_routes(app, database_manager, camera_manager=None, paxton_integration=None, nayax_integration=None):
    """
    Register API routes with the Flask app.
    
    Args:
        app: Flask application instance
        database_manager: Database manager instance
        camera_manager: Camera manager instance
        paxton_integration: Paxton integration instance
        nayax_integration: Nayax integration instance
    """
    # Initialize routes with database manager and camera manager
    init_api_routes(database_manager, camera_manager, paxton_integration, nayax_integration)
    
    # Register blueprint
    app.register_blueprint(api_bp)
    
    return app
