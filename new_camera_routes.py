# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Camera routes for the VisiGate web application.

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
    """
    Camera management page.
    Displays a list of all registered cameras and their status.
    """
    # Initialize variables to ensure they're always defined
    cameras_dict = {}
    cameras_list = []
    stats = {
        "total": 0,
        "online": 0,
        "offline": 0,
        "issues": 0,
        "avg_fps": "24.5"
    }
    
    try:
        # Initialize camera manager if needed
        global onvif_camera_manager
        if onvif_camera_manager is None:
            init_camera_manager(current_app.config)
        
        # Get cameras with proper error handling
        if onvif_camera_manager:
            try:
                # Try to get cameras using get_all_cameras method
                if hasattr(onvif_camera_manager, "get_all_cameras"):
                    cameras_dict = onvif_camera_manager.get_all_cameras()
                # Fallback to accessing cameras attribute directly
                elif hasattr(onvif_camera_manager, "cameras"):
                    cameras_dict = onvif_camera_manager.cameras
                
                # Convert dictionary to list for template if needed
                if isinstance(cameras_dict, dict):
                    for camera_id, camera_info in cameras_dict.items():
                        try:
                            camera = {
                                "id": camera_id,
                                "name": f"Camera {camera_id}",
                                "location": "Unknown",
                                "status": "unknown",
                                "manufacturer": "Unknown",
                                "model": "Unknown"
                            }
                            
                            # Try to extract info if available
                            if isinstance(camera_info, dict):
                                camera["name"] = camera_info.get("name", camera["name"])
                                camera["location"] = camera_info.get("location", camera["location"])
                                camera["status"] = camera_info.get("status", camera["status"])
                                camera["manufacturer"] = camera_info.get("manufacturer", camera["manufacturer"])
                                camera["model"] = camera_info.get("model", camera["model"])
                            
                            cameras_list.append(camera)
                        except Exception as e:
                            logger.error(f"Error processing camera {camera_id}: {str(e)}")
            except Exception as e:
                logger.error(f"Error getting cameras: {str(e)}")
        
        # Calculate camera stats based on the cameras we have
        stats = {
            "total": len(cameras_list),
            "online": sum(1 for c in cameras_list if c.get("status") == "online"),
            "offline": sum(1 for c in cameras_list if c.get("status") == "offline"),
            "issues": sum(1 for c in cameras_list if c.get("status") not in ["online", "offline"]),
            "avg_fps": "24.5"  # Default value
        }
    except Exception as e:
        logger.error(f"Error in cameras route: {str(e)}")
    
    # Always return the template with the required variables
    return render_template("cameras.html", cameras=cameras_list, stats=stats)

@camera_bp.route('/cameras/discover', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def discover_cameras():
    """
    Discover ONVIF cameras on the network.
    """
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

@camera_bp.route('/cameras/add', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def add_camera():
    """
    Add a new camera with credentials.
    """
    # Validate CSRF token
    if request.form.get('csrf_token') != user_manager.get_csrf_token():
        return jsonify({'success': False, 'error': 'Missing CSRF token'}), 400
    
    # Initialize camera manager if needed
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    # Check if we have onvif installed
    if onvif_camera_manager is None:
        return jsonify({'success': False, 'error': 'ONVIF camera support not available'}), 400
    
    # Get camera info from form
    camera_info = {
        'ip': request.form.get('ip'),
        'port': int(request.form.get('port', 80)),
        'username': request.form.get('username'),
        'password': request.form.get('password'),
        'name': request.form.get('name', f"Camera {request.form.get('ip')}"),
        'location': request.form.get('location', 'Unknown'),
        'manufacturer': request.form.get('manufacturer', 'Unknown'),
        'model': request.form.get('model', 'Unknown'),
        'status': 'offline'
    }
    
    # Add camera
    try:
        camera_id = onvif_camera_manager.add_camera(camera_info)
        return jsonify({'success': True, 'camera_id': camera_id})
    except Exception as e:
        logger.error(f"Error adding camera: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@camera_bp.route('/cameras/stream/<camera_id>')
@login_required(user_manager)
def camera_stream(camera_id):
    """
    Stream video from a camera.
    """
    # Initialize camera manager if needed
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    # Check if we have onvif installed
    if onvif_camera_manager is None:
        return "<h1>ONVIF camera support not available</h1>", 400
    
    # Get camera stream
    try:
        stream_url = onvif_camera_manager.get_camera_stream(camera_id)
        if stream_url:
            return f'<img src="{stream_url}" alt="Camera Stream">'
        else:
            return "<h1>Camera stream not available</h1>", 404
    except Exception as e:
        logger.error(f"Error getting camera stream: {str(e)}")
        return f"<h1>Error getting camera stream</h1><p>{str(e)}</p>", 500

@camera_bp.route('/cameras/settings/<camera_id>', methods=['GET', 'POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def camera_settings(camera_id):
    """
    Camera settings page.
    """
    # Initialize camera manager if needed
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    # Check if we have onvif installed
    if onvif_camera_manager is None:
        return "<h1>ONVIF camera support not available</h1>", 400
    
    # Get camera info
    try:
        cameras = onvif_camera_manager.get_all_cameras()
        camera = cameras.get(camera_id)
        if not camera:
            return "<h1>Camera not found</h1>", 404
        
        # Handle POST request
        if request.method == 'POST':
            # Validate CSRF token
            if request.form.get('csrf_token') != user_manager.get_csrf_token():
                return jsonify({'success': False, 'error': 'Missing CSRF token'}), 400
            
            # Update camera settings
            camera['name'] = request.form.get('name', camera['name'])
            camera['location'] = request.form.get('location', camera['location'])
            camera['username'] = request.form.get('username', camera['username'])
            camera['password'] = request.form.get('password', camera['password'])
            camera['port'] = int(request.form.get('port', camera['port']))
            camera['manufacturer'] = request.form.get('manufacturer', camera['manufacturer'])
            camera['model'] = request.form.get('model', camera['model'])
            camera['use_for_recognition'] = request.form.get('use_for_recognition') == 'true'
            camera['wdr_enabled'] = request.form.get('wdr_enabled', 'false').lower() == 'true'
            
            # Save camera settings
            onvif_camera_manager.update_camera(camera_id, camera)
            
            return jsonify({'success': True})
        
        # Render settings page
        return render_template('camera_settings.html', camera=camera, camera_id=camera_id)
    except Exception as e:
        logger.error(f"Error accessing camera settings: {str(e)}")
        return f"<h1>Error accessing camera settings</h1><p>{str(e)}</p>", 500

# Register the blueprint with the application
def register_camera_routes(app):
    """
    Register camera routes with the application.
    """
    app.register_blueprint(camera_bp)
    
    # Initialize camera manager
    init_camera_manager(app.config)
