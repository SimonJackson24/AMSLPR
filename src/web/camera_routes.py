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

import nest_asyncio
nest_asyncio.apply()

def setup_routes(app, detector, db_manager):
    """Set up camera routes with the detector and database manager."""
    global _detector, _db_manager, _app
    _detector = detector
    _db_manager = db_manager
    _app = app
    
    # Initialize camera state
    global camera_state
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
    global onvif_camera_manager
    
    # Don't initialize if already initialized
    if onvif_camera_manager is not None:
        return onvif_camera_manager
    
    try:
        # Import here to avoid circular imports
        from src.recognition.onvif_camera import ONVIFCameraManager
        logger.debug("Initializing ONVIFCameraManager with config: %s", config.get('camera', {}))
        onvif_camera_manager = ONVIFCameraManager(config.get('camera', {}))
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
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    cameras = onvif_camera_manager.get_all_cameras() if onvif_camera_manager else {}
    
    # Calculate camera stats
    stats = {
        'total': len(cameras),
        'online': sum(1 for c in cameras.values() if c.get('status', 'offline') == 'online'),
        'offline': sum(1 for c in cameras.values() if c.get('status', 'offline') == 'offline'),
        'issues': sum(1 for c in cameras.values() if c.get('status', '') == 'error')
    }
    
    return render_template('cameras.html', cameras=cameras, stats=stats)

@camera_bp.route('/cameras/add', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def add_camera():
    """Add a new camera with credentials."""
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Request must be JSON'}), 400

    # Validate CSRF token
    csrf_token = request.headers.get('X-CSRFToken')
    if not csrf_token:
        return jsonify({'success': False, 'error': 'Missing CSRF token'}), 400
        
    data = request.get_json()
    required_fields = ['ip', 'username', 'password']
    
    # Validate required fields
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
            
    try:
        # Import here to avoid circular imports
        from src.recognition.onvif_camera import ONVIFCamera
        
        # Get port with default of 80
        port = int(data.get('port', 80))
        
        # Try to connect with provided credentials
        camera = ONVIFCamera(
            data['ip'], 
            port,
            data['username'], 
            data['password'], 
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '../recognition/wsdl')
        )
        
        # Get camera info
        device_info = camera.devicemgmt.GetDeviceInformation()
        media_service = camera.create_media_service()
        profiles = media_service.GetProfiles()
        
        if profiles:
            # Get stream URI
            token = profiles[0].token
            stream_setup = {
                'Stream': 'RTP-Unicast',
                'Transport': {'Protocol': 'RTSP'}
            }
            stream_uri = media_service.GetStreamUri(stream_setup, token)
            
            camera_info = {
                'ip': data['ip'],
                'port': port,
                'username': data['username'],
                'password': data['password'],
                'profiles': [{'token': p.token, 'name': p.Name} for p in profiles],
                'manufacturer': device_info.Manufacturer,
                'model': device_info.Model,
                'firmware': device_info.FirmwareVersion,
                'serial': device_info.SerialNumber,
                'stream_uri': stream_uri.Uri,
                'status': 'connected'
            }
            
            # Add to camera manager
            if onvif_camera_manager:
                onvif_camera_manager.add_camera(camera_info)
                
            return jsonify({
                'success': True,
                'camera': camera_info,
                'message': 'Camera added successfully'
            }), 200
            
    except Exception as e:
        logger.error(f"Error adding camera: {str(e)}")
        return jsonify({'success': False, 'error': f'Error adding camera: {str(e)}'}), 500

@camera_bp.route('/cameras/add', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def add_camera_old():
    """Add a new camera."""
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    try:
        # Get form data
        camera_id = request.form.get('camera_id')
        name = request.form.get('name')
        location = request.form.get('location')
        ip = request.form.get('ip')
        port = int(request.form.get('port', 80))
        username = request.form.get('username', 'admin')
        password = request.form.get('password', 'admin')
        rtsp_url = request.form.get('rtsp_url')  # Get RTSP URL from form
        enabled = request.form.get('enabled') == 'true'
        use_for_recognition = request.form.get('use_for_recognition') == 'true'
        
        # Get image enhancement settings
        hlc_enabled = request.form.get('hlc_enabled') == 'true'
        wdr_enabled = request.form.get('wdr_enabled') == 'true'
        hlc_level = float(request.form.get('hlc_level', 0.5))
        wdr_level = float(request.form.get('wdr_level', 0.5))
        
        if not camera_id or not ip:
            flash('Camera ID and IP address are required', 'error')
            return redirect(url_for('camera.cameras'))
        
        # Store credentials securely
        credentials = {'username': username, 'password': password}
        encrypted_credentials = credential_manager.encrypt_credentials(credentials)
        
        # Add camera to configuration
        camera_config = {
            'id': camera_id,
            'name': name,
            'location': location,
            'ip': ip,
            'port': port,
            'encrypted_credentials': encrypted_credentials,
            'enabled': enabled,
            'use_for_recognition': use_for_recognition,
            'hlc_enabled': hlc_enabled,
            'hlc_level': hlc_level,
            'wdr_enabled': wdr_enabled,
            'wdr_level': wdr_level
        }
        
        # Update application config
        app_config = current_app.config.get('AMSLPR_CONFIG', {})
        cameras_config = app_config.get('cameras', [])
        
        # Check if camera with this ID already exists
        existing_camera = next((c for c in cameras_config if c.get('id') == camera_id), None)
        if existing_camera:
            # Update existing camera
            existing_camera.update(camera_config)
        else:
            # Add new camera
            cameras_config.append(camera_config)
        
        # Update config
        app_config['cameras'] = cameras_config
        current_app.config['AMSLPR_CONFIG'] = app_config
        
        # Save config to file
        config_file = current_app.config.get('CONFIG_FILE')
        if config_file:
            with open(config_file, 'w') as f:
                import json
                json.dump(app_config, f, indent=4)
        
        # Add camera to manager
        success = onvif_camera_manager.add_camera(
            camera_id=camera_id,
            ip=ip,
            port=port,
            name=name,
            location=location,
            username=username,
            password=password,
            rtsp_url=rtsp_url  # Pass RTSP URL to camera manager
        )
        
        if success:
            # Configure camera imaging settings
            onvif_camera_manager.configure_camera_imaging(
                camera_id=camera_id,
                hlc_enabled=hlc_enabled,
                hlc_level=hlc_level,
                wdr_enabled=wdr_enabled,
                wdr_level=wdr_level
            )
            flash(f'Camera {name} configuration saved. Connection will be established in the background.', 'success')
        else:
            flash('Failed to add camera. ONVIF camera manager not initialized.', 'error')
    
    except Exception as e:
        logger.error(f"Error adding camera: {e}")
        flash(f'Error adding camera: {str(e)}', 'error')
    
    return redirect(url_for('camera.cameras'))

@camera_bp.route('/cameras/settings/<camera_id>', methods=['GET', 'POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
async def camera_settings(camera_id):
    """Camera settings page."""
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    if onvif_camera_manager:
        camera = onvif_camera_manager.get_camera_info(camera_id)
    else:
        camera = None
    
    if not camera:
        flash('Camera not found', 'error')
        return redirect(url_for('camera.cameras'))
    
    if request.method == 'POST':
        hlc_enabled = request.form.get('hlc_enabled', 'false').lower() == 'true'
        wdr_enabled = request.form.get('wdr_enabled', 'false').lower() == 'true'
        hlc_level = float(request.form.get('hlc_level', 0.5))
        wdr_level = float(request.form.get('wdr_level', 0.5))
        
        if onvif_camera_manager:
            success = await onvif_camera_manager.configure_camera_imaging(
                camera_id=camera_id,
                hlc_enabled=hlc_enabled,
                hlc_level=hlc_level,
                wdr_enabled=wdr_enabled,
                wdr_level=wdr_level
            )
            
            if success:
                flash('Camera settings updated successfully', 'success')
            else:
                flash('Failed to update camera settings', 'error')
        else:
            flash('Failed to update camera settings. ONVIF camera manager not initialized.', 'error')
        
        return redirect(url_for('camera.camera_settings', camera_id=camera_id))
    
    return render_template('camera_settings.html', camera=camera)

@camera_bp.route('/camera/settings')
def camera_settings_index():
    """Camera settings index page."""
    # Get camera manager
    camera_manager = onvif_camera_manager
    
    # Get all cameras
    cameras = {}
    if camera_manager:
        cameras = camera_manager.get_all_cameras()
    
    # Get global camera settings
    config = current_app.config.get('AMSLPR_CONFIG', {})
    camera_config = config.get('camera', {})
    
    # Global settings
    global_settings = {
        'discovery_enabled': camera_config.get('discovery_enabled', True),
        'discovery_interval': camera_config.get('discovery_interval', 60),
        'default_username': camera_config.get('default_username', 'admin'),
        'default_password': camera_config.get('default_password', '*****'),
        'auto_connect': camera_config.get('auto_connect', True),
        'reconnect_attempts': camera_config.get('reconnect_attempts', 3),
        'reconnect_interval': camera_config.get('reconnect_interval', 10)
    }
    
    # Recognition settings
    recognition_config = config.get('recognition', {})
    settings = {
        'detection_confidence': recognition_config.get('detection_confidence', 0.7),
        'min_plate_size': recognition_config.get('min_plate_size', 20),
        'max_plate_size': recognition_config.get('max_plate_size', 200),
        'recognition_interval': recognition_config.get('recognition_interval', 1.0),
        'detection_path': recognition_config.get('detection_path', '/var/lib/amslpr/detection')
    }
    
    return render_template('camera_settings.html', 
                           cameras=cameras, 
                           global_settings=global_settings,
                           camera_count=len(cameras),
                           settings=settings)

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

def register_camera_routes(app, detector, db_manager):
    """Register camera routes with the Flask application."""
    global _detector, _db_manager, _app
    _detector = detector
    _db_manager = db_manager
    _app = app
    
    # Register the blueprint
    app.register_blueprint(camera_bp, url_prefix='')
    
    # Set up routes
    setup_routes(app, detector, db_manager)
    
    # Initialize camera manager
    init_camera_manager(app.config)
