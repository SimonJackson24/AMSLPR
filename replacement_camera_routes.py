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
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, Response
from werkzeug.utils import secure_filename

from src.web.auth import login_required, permission_required, user_manager
from src.recognition.onvif_camera import ONVIFCameraManager

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
camera_bp = Blueprint('camera_bp', __name__)

# Initialize camera manager
onvif_camera_manager = None

def init_camera_manager(config):
    """
    Initialize the camera manager with the application configuration.
    
    Args:
        config (dict): Application configuration
        
    Returns:
        ONVIFCameraManager: Initialized camera manager instance
    """
    global onvif_camera_manager
    
    if onvif_camera_manager is not None:
        return onvif_camera_manager
    
    try:
        # Import here to avoid circular imports
        from src.recognition.onvif_camera import ONVIFCameraManager
        
        # Initialize the camera manager
        onvif_camera_manager = ONVIFCameraManager(config.get('camera', {}))
        logger.info("Camera manager initialized successfully")
        return onvif_camera_manager
    except ImportError:
        logger.warning("ONVIF camera support not available")
        return None
    except Exception as e:
        logger.error(f"Error initializing camera manager: {str(e)}")
        return None

@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    # Create minimal data for the template
    cameras_list = []
    stats = {
        "total": 0,
        "online": 0,
        "offline": 0,
        "issues": 0,
        "avg_fps": "24.5"
    }
    
    # Return the template with the required variables
    return render_template("cameras.html", cameras=cameras_list, stats=stats)

@camera_bp.route('/cameras/discover', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def discover_cameras():
    """Discover ONVIF cameras on the network."""
    # Initialize camera manager if needed
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    # Check if we have onvif installed
    if onvif_camera_manager is None:
        return jsonify({'success': False, 'error': 'ONVIF camera support not available'}), 400
    
    # Discover cameras
    try:
        cameras = onvif_camera_manager.discover_cameras()
        return jsonify({'success': True, 'cameras': cameras})
    except Exception as e:
        logger.error(f"Error discovering cameras: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Register the blueprint with the application
def register_camera_routes(app):
    """Register camera routes with the application."""
    app.register_blueprint(camera_bp)
    
    # Initialize camera manager
    init_camera_manager(app.config)
