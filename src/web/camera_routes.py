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

from src.recognition.onvif_camera import ONVIFCameraManager
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
    Initialize the ONVIF camera manager.
    
    Args:
        config (dict): Configuration dictionary
    """
    global onvif_camera_manager
    if onvif_camera_manager is None:
        onvif_camera_manager = ONVIFCameraManager(config.get('camera', {}))
        logger.info("ONVIF camera manager initialized")

@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    cameras = onvif_camera_manager.get_all_cameras()
    
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
async def add_camera():
    """Add a new camera."""
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    camera_id = request.form.get('camera_id')
    name = request.form.get('name')
    location = request.form.get('location')
    ip = request.form.get('ip')
    port = int(request.form.get('port', 80))
    username = request.form.get('username', 'admin')
    password = request.form.get('password', 'admin')
    
    if not camera_id or not ip:
        flash('Camera ID and IP address are required', 'error')
        return redirect(url_for('camera.cameras'))
    
    success = await onvif_camera_manager.add_camera(
        camera_id=camera_id,
        ip=ip,
        port=port,
        name=name,
        location=location
    )
    
    if success:
        # Configure camera settings if provided
        hlc_enabled = request.form.get('hlc_enabled', 'false').lower() == 'true'
        wdr_enabled = request.form.get('wdr_enabled', 'false').lower() == 'true'
        hlc_level = float(request.form.get('hlc_level', 0.5))
        wdr_level = float(request.form.get('wdr_level', 0.5))
        
        await onvif_camera_manager.configure_camera_imaging(
            camera_id=camera_id,
            hlc_enabled=hlc_enabled,
            hlc_level=hlc_level,
            wdr_enabled=wdr_enabled,
            wdr_level=wdr_level
        )
        flash(f'Camera {name} added successfully', 'success')
    else:
        flash('Failed to add camera', 'error')
    
    return redirect(url_for('camera.cameras'))

@camera_bp.route('/cameras/settings/<camera_id>', methods=['GET', 'POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
async def camera_settings(camera_id):
    """Camera settings page."""
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    camera = onvif_camera_manager.get_camera_info(camera_id)
    if not camera:
        flash('Camera not found', 'error')
        return redirect(url_for('camera.cameras'))
    
    if request.method == 'POST':
        hlc_enabled = request.form.get('hlc_enabled', 'false').lower() == 'true'
        wdr_enabled = request.form.get('wdr_enabled', 'false').lower() == 'true'
        hlc_level = float(request.form.get('hlc_level', 0.5))
        wdr_level = float(request.form.get('wdr_level', 0.5))
        
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
        
        return redirect(url_for('camera.camera_settings', camera_id=camera_id))
    
    return render_template('camera_settings.html', camera=camera)

@camera_bp.route('/cameras/stream/<camera_id>')
@login_required(user_manager)
def camera_feed(camera_id):
    """Stream video feed from a camera."""
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    stream_url = onvif_camera_manager.get_stream_url(camera_id)
    if not stream_url:
        return "Stream not available", 404
    
    # Return an img tag that points to the RTSP stream
    # The frontend will handle displaying this using appropriate video player
    return f'<img src="{stream_url}" alt="Camera Stream">'

def register_camera_routes(app, detector, db_manager):
    """Register camera routes with the Flask application."""
    global _detector, _db_manager, _app
    _detector = detector
    _db_manager = db_manager
    _app = app
    
    # Register the blueprint
    app.register_blueprint(camera_bp, url_prefix='/camera')
    
    # Set up routes
    setup_routes(app, detector, db_manager)
    
    # Initialize camera manager
    init_camera_manager(app.config)
