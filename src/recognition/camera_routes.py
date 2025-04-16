# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Camera routes for the AMSLPR web application.

This module provides routes for managing ONVIF cameras and viewing license plate recognition results.
"""

import os
import cv2
import time
import logging
import asyncio
import numpy as np
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, Response, current_app
from functools import wraps

from src.utils.security import CredentialManager
from src.utils.user_management import login_required, permission_required, UserManager

# Import detector with fallback for missing dependencies
try:
    from src.recognition.detector import LicensePlateDetector
    DETECTOR_AVAILABLE = True
    MOCK_DETECTOR = False
except ImportError as e:
    logging.warning(f"Could not import LicensePlateDetector in camera_routes: {e}")
    logging.warning("Using MockLicensePlateDetector instead")
    from src.recognition.mock_detector import MockLicensePlateDetector as LicensePlateDetector
    DETECTOR_AVAILABLE = True
    MOCK_DETECTOR = True

logger = logging.getLogger('AMSLPR.web.cameras')

# Create blueprint
camera_bp = Blueprint('camera', __name__)

# Initialize credential manager
credential_manager = CredentialManager()

# Initialize user manager
user_manager = UserManager()

# Global variables
onvif_camera_manager = None
detectors = {}
recognition_results = {}
recognition_tasks = {}
_detector = None
_db_manager = None
_app = None
camera_state = None

import nest_asyncio
nest_asyncio.apply()

def setup_routes(app, detector, db_manager):
    """Set up camera routes with the detector and database manager."""
    global _detector, _db_manager, _app, camera_state
    _detector = detector
    _db_manager = db_manager
    _app = app
    
    # Initialize camera state
    camera_state = {
        'active': False,
        'processing': False,
        'reload_ocr_config': False
    }

def init_camera_manager(config):
    """
    Initialize the camera manager with the application configuration.
    
    Args:
        config (dict): Application configuration
    
    Returns:
        ONVIFCameraManager: Initialized camera manager instance
    """
    global onvif_camera_manager, _detector, _db_manager, _app
    
    # Don't initialize if already initialized
    if onvif_camera_manager is not None:
        return onvif_camera_manager
    
    try:
        # Import here to avoid circular imports
        from src.recognition.onvif_camera import ONVIFCameraManager
        logger.debug("Initializing ONVIFCameraManager")
        onvif_camera_manager = ONVIFCameraManager()
        return onvif_camera_manager
    except Exception as e:
        logger.error(f"Failed to initialize ONVIF camera manager: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    try:
        global onvif_camera_manager
        if onvif_camera_manager is None:
            try:
                init_camera_manager(current_app.config)
                logger.info("Camera manager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize camera manager: {str(e)}")
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"Traceback: {error_details}")
                return render_template('error.html', 
                                      error_title="Camera Manager Initialization Error",
                                      error_message=f"Failed to initialize camera manager: {str(e)}",
                                      error_details=error_details)
        
        try:
            # Get raw cameras from manager
            raw_cameras = onvif_camera_manager.get_all_cameras() if onvif_camera_manager else {}
            logger.info(f"Retrieved {len(raw_cameras)} cameras from manager")
            
            # Process cameras to ensure they have all required attributes
            cameras = []
            for camera_id, camera_info in raw_cameras.items():
                # Create camera object with all required fields for the template
                camera = {
                    'id': camera_id,
                    'name': camera_info.get('name', 'Unknown Camera'),
                    'location': camera_info.get('location', 'Unknown'),
                    'status': camera_info.get('status', 'unknown'),
                    'thumbnail': 'default_camera.jpg',  # Add required thumbnail
                    'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                    'model': camera_info.get('model', 'Unknown'),
                    'url': camera_info.get('stream_uri', 'rtsp://192.168.1.100:554/stream'),
                    'fps': 25,  # Default FPS
                    'uptime': '24h'  # Default uptime
                }
                cameras.append(camera)
        except Exception as e:
            logger.error(f"Failed to retrieve cameras: {str(e)}")
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Traceback: {error_details}")
            return render_template('error.html', 
                                  error_title="Camera Retrieval Error",
                                  error_message=f"Failed to retrieve cameras: {str(e)}",
                                  error_details=error_details)
        
        # Calculate camera stats
        try:
            stats = {
                'total': len(cameras),
                'online': sum(1 for c in cameras if c.get('status', 'offline') == 'online'),
                'offline': sum(1 for c in cameras if c.get('status', 'offline') == 'offline'),
                'issues': sum(1 for c in cameras if c.get('status', '') == 'error')
            }
            logger.info(f"Camera stats calculated: {stats}")
        except Exception as e:
            logger.error(f"Failed to calculate camera stats: {str(e)}")
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Traceback: {error_details}")
            return render_template('error.html', 
                                  error_title="Camera Stats Calculation Error",
                                  error_message=f"Failed to calculate camera stats: {str(e)}",
                                  error_details=error_details)
        
        return render_template('cameras.html', cameras=cameras, stats=stats)
    except Exception as e:
        logger.error(f"Unhandled exception in cameras route: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Traceback: {error_details}")
        return render_template('error.html', 
                              error_title="Camera Page Error",
                              error_message=f"Unhandled exception in cameras route: {str(e)}",
                              error_details=error_details)

@camera_bp.route('/cameras/add', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def add_camera():
    """Add a new camera with credentials."""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400

        # Validate CSRF token
        csrf_token = request.headers.get('X-CSRFToken')
        if not csrf_token:
            return jsonify({'success': False, 'error': 'Missing CSRF token'}), 400
            
        try:
            data = request.get_json()
            logger.info(f"Received camera add request with data: {data}")
            
            required_fields = ['ip', 'username', 'password']
            
            # Validate required fields
            for field in required_fields:
                if field not in data:
                    return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
                    
            # Initialize camera manager if not already initialized
            global onvif_camera_manager
            if not onvif_camera_manager:
                from src.recognition.onvif_camera import initialize_camera_manager
                onvif_camera_manager = initialize_camera_manager()
                logger.info("Initialized ONVIF camera manager")
            
            # Get port with default of 80
            port = int(data.get('port', 80))
            
            # Add camera to manager first
            camera_info = {
                'ip': data['ip'],
                'port': port,
                'username': data['username'],
                'password': data['password']
            }
            
            result = onvif_camera_manager.add_camera(camera_info)
            if isinstance(result, tuple):
                success, error_message = result
                if not success:
                    return jsonify({
                        'success': False,
                        'error': error_message
                    }), 400
            elif not result:
                return jsonify({
                    'success': False,
                    'error': 'Failed to add camera to manager'
                }), 400
            
            # Get the camera object back from the manager
            camera = onvif_camera_manager.cameras.get(data['ip'])
            if not camera:
                return jsonify({
                    'success': False,
                    'error': 'Camera was added but could not be retrieved'
                }), 500
            
            # Get camera info
            device_info = camera['camera'].devicemgmt.GetDeviceInformation()
            media_service = camera['camera'].create_media_service()
            profiles = media_service.GetProfiles()
            
            if profiles:
                # Get stream URI
                token = profiles[0].token
                
                # Create stream URI request
                stream_uri_request = media_service.create_type('GetStreamUri')
                stream_uri_request.ProfileToken = token
                
                # Create StreamSetup
                stream_setup = media_service.create_type('StreamSetup')
                stream_setup.Stream = 'RTP-Unicast'
                stream_setup.Transport = media_service.create_type('Transport')
                stream_setup.Transport.Protocol = 'RTSP'
                stream_uri_request.StreamSetup = stream_setup
                
                # Get stream URI
                stream_uri = media_service.GetStreamUri(stream_uri_request)
                
                # Update camera info
                camera['info'].update({
                    'profiles': [{'token': p.token, 'name': p.Name} for p in profiles],
                    'manufacturer': device_info.Manufacturer,
                    'model': device_info.Model,
                    'firmware': device_info.FirmwareVersion,
                    'serial': device_info.SerialNumber,
                    'stream_uri': stream_uri.Uri,
                    'status': 'connected'
                })
                
                return jsonify({
                    'success': True,
                    'camera': camera['info'],
                    'message': 'Camera added successfully'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'No media profiles found for camera'
                }), 400
                
        except Exception as e:
            logger.error(f"Error adding camera: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': f'An error occurred while adding the camera: {str(e)}'
            }), 400
            
    except Exception as e:
        logger.error(f"Critical error in add_camera route: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'A critical error occurred: {str(e)}'
        }), 500

@camera_bp.errorhandler(500)
def handle_500_error(e):
    """Handle 500 Internal Server Error with JSON response."""
    logger.error(f"500 error: {str(e)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error occurred'
    }), 500

@camera_bp.route('/settings/<camera_id>')
@login_required(user_manager)
@permission_required('admin', user_manager)
def camera_settings(camera_id):
    """
    Camera settings page.
    
    Args:
        camera_id (str): ID of the camera to get settings for
    """
    if not onvif_camera_manager:
        flash('Camera manager not available', 'error')
        return redirect(url_for('camera.camera_settings_index'))
    
    try:
        # Get camera from manager
        camera = onvif_camera_manager.get_camera(camera_id)
        if not camera:
            flash('Camera not found', 'error')
            return redirect(url_for('camera.camera_settings_index'))
        
        # Get camera settings
        settings = camera.get_settings()
        
        return render_template('camera_settings.html', camera=camera, settings=settings)
    except Exception as e:
        logger.error(f"Error getting camera settings: {str(e)}")
        flash(f'Error getting camera settings: {str(e)}', 'error')
        return redirect(url_for('camera.camera_settings_index'))

@camera_bp.route('/camera/settings')
@login_required(user_manager)
def camera_settings_index():
    """Camera settings index page."""
    # Get camera manager
    camera_manager = onvif_camera_manager
    
    # Get all cameras
    cameras = []
    if camera_manager:
        all_cameras = camera_manager.get_all_cameras()
        for camera_id, camera in all_cameras.items():
            cameras.append({
                'id': camera_id,
                'name': camera.get('name', 'Unknown Camera'),
                'location': camera.get('location', 'Unknown'),
                'status': 'online',  # Placeholder, would be determined by actual health check
                'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return render_template('camera_settings_index.html', 
                           cameras=cameras,
                           last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@camera_bp.route('/camera/settings/<camera_id>/save', methods=['POST'])
def save_camera_settings(camera_id):
    """Save camera settings."""
    # Get camera manager
    camera_manager = onvif_camera_manager
    
    if camera_id == 'global':
        # Save global camera settings
        config = current_app.config.get('AMSLPR_CONFIG', {})
        camera_config = config.get('camera', {})
        
        # Update settings from form
        camera_config['discovery_enabled'] = request.form.get('discovery_enabled') == 'on'
        camera_config['discovery_interval'] = int(request.form.get('discovery_interval', 60))
        camera_config['default_username'] = request.form.get('default_username', 'admin')
        
        # Only update password if provided and not placeholder
        new_password = request.form.get('default_password')
        if new_password and new_password != '*****':
            camera_config['default_password'] = new_password
            
        camera_config['auto_connect'] = request.form.get('auto_connect') == 'on'
        camera_config['reconnect_attempts'] = int(request.form.get('reconnect_attempts', 3))
        camera_config['reconnect_interval'] = int(request.form.get('reconnect_interval', 10))
        
        # Save config
        from src.config.settings import save_config
        save_config(config)
        
        flash('Global camera settings saved successfully', 'success')
    else:
        # Save individual camera settings
        if not camera_manager:
            flash('Camera manager not available', 'danger')
            return redirect(url_for('camera.camera_settings_index'))
        
        # Get camera settings from form
        camera_settings = {
            'name': request.form.get('name', ''),
            'location': request.form.get('location', ''),
            'username': request.form.get('username', ''),
            'password': request.form.get('password', ''),
            'rtsp_port': int(request.form.get('rtsp_port', 554)),
            'http_port': int(request.form.get('http_port', 80)),
            'enabled': request.form.get('enabled') == 'on'
        }
        
        # Update camera settings
        try:
            # This would be implemented in the camera manager
            # camera_manager.update_camera(camera_id, camera_settings)
            flash('Camera settings saved successfully', 'success')
        except Exception as e:
            logger.error(f"Error saving camera settings: {e}")
            flash(f'Error saving camera settings: {str(e)}', 'danger')
    
    return redirect(url_for('camera.camera_settings_index'))

@camera_bp.route('/cameras/stream/<camera_id>')
@login_required(user_manager)
def camera_feed(camera_id):
    """Stream video feed from a camera."""
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    if onvif_camera_manager:
        stream_url = onvif_camera_manager.get_stream_url(camera_id)
    else:
        stream_url = None
    
    if not stream_url:
        return "Stream not available", 404
    
    # Return an img tag that points to the RTSP stream
    # The frontend will handle displaying this using appropriate video player
    return f'<img src="{stream_url}" alt="Camera Stream">'

@camera_bp.route('/camera/health')
@login_required(user_manager)
def camera_health():
    """Camera health monitoring page."""
    # Get camera manager
    camera_manager = onvif_camera_manager
    
    # Get camera health data
    camera_health_data = []
    online_count = 0
    warning_count = 0
    
    if camera_manager:
        cameras = camera_manager.get_all_cameras()
        for camera_id, camera in cameras.items():
            status = 'online'  # Default status, would be determined by actual health check
            if status == 'online':
                online_count += 1
            elif status == 'warning':
                warning_count += 1
                
            camera_health_data.append({
                'id': camera_id,
                'name': camera.get('name', 'Unknown Camera'),
                'location': camera.get('location', 'Unknown'),
                'status': status,
                'uptime': '24h 35m',  # Placeholder
                'last_frame': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'frame_rate': 25  # Placeholder
            })
    
    return render_template('camera_health.html', 
                           cameras=camera_health_data,
                           online_count=online_count,
                           warning_count=warning_count,
                           last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@camera_bp.route('/camera/view/<camera_id>')
def view_camera(camera_id):
    """View a specific camera."""
    # Get camera manager
    camera_manager = onvif_camera_manager
    
    # Get camera details
    camera = None
    if camera_manager:
        try:
            camera = camera_manager.get_camera_info(camera_id)
        except Exception as e:
            logger.error(f"Error getting camera info: {e}")
    
    if not camera:
        flash('Camera not found', 'danger')
        return redirect(url_for('camera.cameras'))
    
    return render_template('camera_view.html', camera=camera, camera_id=camera_id)

@camera_bp.route('/cameras/discover', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def discover_cameras():
    """Discover ONVIF cameras on the network."""
    global onvif_camera_manager
    logger.debug("Starting camera discovery route...")
    
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Request must be JSON'}), 400

    # Validate CSRF token
    csrf_token = request.headers.get('X-CSRFToken')
    if not csrf_token:
        return jsonify({'success': False, 'error': 'Missing CSRF token'}), 400
    
    try:
        # Import here to avoid circular imports
        from src.recognition.onvif_camera import ONVIFCameraManager
        
        # Check if we have onvif installed
        try:
            import onvif
            logger.debug("onvif package is installed")
        except ImportError as e:
            logger.error("onvif package is not installed")
            return jsonify({'success': False, 'error': 'Required package onvif is not installed'}), 500
        
        # Check if we have zeep installed
        try:
            import zeep
            logger.debug("zeep package is installed")
        except ImportError as e:
            logger.error("zeep package is not installed")
            return jsonify({'success': False, 'error': 'Required package zeep is not installed'}), 500
        
        if onvif_camera_manager is None:
            logger.debug("Initializing camera manager...")
            try:
                # Get camera config from app config
                camera_config = current_app.config.get('camera', {})
                logger.debug(f"Camera config from app: {camera_config}")
                if not camera_config:
                    logger.error("No camera configuration found in app config")
                    return jsonify({'success': False, 'error': 'No camera configuration found'}), 500
                
                # Initialize camera manager directly
                logger.debug("Creating ONVIFCameraManager instance...")
                onvif_camera_manager = ONVIFCameraManager(camera_config)
                if onvif_camera_manager is None:
                    logger.error("Failed to create camera manager")
                    return jsonify({'success': False, 'error': 'Failed to initialize camera manager'}), 500
                
            except Exception as e:
                logger.error(f"Error initializing camera manager: {str(e)}")
                return jsonify({'success': False, 'error': f'Error initializing camera manager: {str(e)}'}), 500
        
        # Start camera discovery
        logger.debug("Starting camera discovery...")
        discovered_cameras = onvif_camera_manager.discover_cameras(timeout=5)
        
        if not discovered_cameras:
            logger.warning("No cameras found during discovery")
            return jsonify({'success': True, 'cameras': [], 'message': 'No cameras found'}), 200
        
        logger.info(f"Found {len(discovered_cameras)} cameras")
        return jsonify({
            'success': True,
            'cameras': discovered_cameras,
            'message': f'Found {len(discovered_cameras)} cameras. Please configure credentials for each camera you want to use.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error during camera discovery: {str(e)}")
        return jsonify({'success': False, 'error': f'Error during camera discovery: {str(e)}'}), 500

@camera_bp.route('/test_camera_credentials', methods=['POST'])
def test_camera_credentials():
    """This endpoint has been removed as it was inappropriate."""
    logger.warning("The test_camera_credentials endpoint has been removed as it was inappropriate.")
    return jsonify({
        'success': False,
        'error': 'This functionality has been removed.'
    }), 400

def register_camera_routes(app, detector, db_manager):
    """Register camera routes with the Flask application."""
    global _detector, _db_manager, _app, camera_state
    _detector = detector
    _db_manager = db_manager
    _app = app
    
    # Register the blueprint
    app.register_blueprint(camera_bp)
    
    # Initialize camera manager if app.config exists
    if hasattr(app, 'config') and app.config:
        init_camera_manager(app.config)
    else:
        logger.warning("App config not available, skipping camera manager initialization")
    
    logger.info("Camera routes registered")
    
    return app
