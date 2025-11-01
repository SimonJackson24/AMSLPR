# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Emergency fix for camera routes in the VisiGate web application.
This module provides a simplified version of the camera routes to resolve the 500 error.
"""

import os
import logging
import traceback
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from functools import wraps

# Import user management with fallback
try:
    from src.web.user_management import login_required, permission_required, UserManager
    from src.utils.security import CredentialManager
except ImportError:
    from src.utils.user_management import login_required, permission_required, UserManager
    from src.utils.security import CredentialManager

# Setup logging
logger = logging.getLogger('VisiGate.web.cameras')

# Create blueprint
camera_bp = Blueprint('camera', __name__)

# Initialize managers
user_manager = UserManager()
credential_manager = CredentialManager()

# Global variables
onvif_camera_manager = None
db_manager = None

# Import database manager with fallback
try:
    from src.database.db_manager import DatabaseManager
except ImportError as e:
    try:
        from src.db.manager import DatabaseManager
        logger.warning("Using alternative DatabaseManager import path")
    except ImportError as e:
        logger.warning(f"Could not import DatabaseManager: {e}")
        logger.warning("Database functionality will be limited")
        DatabaseManager = None

def init_camera_manager(config):
    """Initialize the camera manager with minimal dependencies."""
    global onvif_camera_manager, db_manager
    
    logger.info("Initializing camera manager with minimal dependencies")
    
    # Initialize database manager if not already initialized
    if db_manager is None and DatabaseManager is not None:
        try:
            logger.info("Initializing database manager")
            db_manager = DatabaseManager(config)
            logger.info("Database manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {str(e)}")
            db_manager = None
    
    # Create a simple mock camera manager if needed
    if onvif_camera_manager is None:
        try:
            # Try to import the real camera manager
            try:
                from src.recognition.onvif_camera import ONVIFCameraManager
                onvif_camera_manager = ONVIFCameraManager()
                logger.info("Using real ONVIFCameraManager")
            except ImportError:
                # If import fails, create a simple mock manager
                logger.warning("Could not import ONVIFCameraManager, using mock")
                class MockCameraManager:
                    def __init__(self):
                        self.cameras = {}
                    
                    def get_all_cameras_list(self):
                        """Return a list of all cameras."""
                        return []
                
                onvif_camera_manager = MockCameraManager()
                logger.info("Using MockCameraManager instead")
        except Exception as e:
            logger.error(f"Failed to initialize any camera manager: {str(e)}")
            logger.error(traceback.format_exc())
            onvif_camera_manager = None
    
    return onvif_camera_manager

@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Simplified camera management page to avoid 500 errors."""
    try:
        # Initialize camera manager if needed
        if onvif_camera_manager is None:
            init_camera_manager(current_app.config)
        
        # Get cameras - use an empty list if anything fails
        cameras = []
        try:
            if onvif_camera_manager and hasattr(onvif_camera_manager, 'get_all_cameras_list'):
                cameras = onvif_camera_manager.get_all_cameras_list()
            elif onvif_camera_manager and hasattr(onvif_camera_manager, 'cameras'):
                # Simplified camera extraction
                for camera_id, camera_data in onvif_camera_manager.cameras.items():
                    try:
                        cameras.append({
                            'id': camera_id,
                            'name': 'Camera ' + str(camera_id),
                            'location': 'Unknown',
                            'status': 'unknown',
                            'manufacturer': 'Unknown',
                            'model': 'Unknown'
                        })
                    except Exception as e:
                        logger.error(f"Error processing camera {camera_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Error retrieving cameras: {str(e)}")
            # Continue with empty list
        
        # Render template with whatever cameras we could get
        return render_template('cameras.html', cameras=cameras)
    except Exception as e:
        logger.error(f"Error in cameras route: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a simple message instead of rendering a template that might fail
        return "<h1>Camera Page Temporarily Unavailable</h1><p>The system is experiencing technical difficulties. Please try again later or contact support.</p>", 503

@camera_bp.route('/cameras/add', methods=['POST'])
@login_required(user_manager)
def add_camera():
    """Add a new camera - simplified version."""
    try:
        # Just return a success message without actually adding a camera
        flash("Camera functionality is currently under maintenance. Please try again later.", "warning")
        return redirect(url_for('camera.cameras'))
    except Exception as e:
        logger.error(f"Error in add_camera route: {str(e)}")
        flash("An error occurred while processing your request.", "danger")
        return redirect(url_for('camera.cameras'))

@camera_bp.route('/cameras/stream/<camera_id>')
@login_required(user_manager)
def camera_stream(camera_id):
    """Stream camera feed - simplified version."""
    try:
        return "<h1>Camera Stream Temporarily Unavailable</h1><p>Camera streaming is currently under maintenance.</p>", 503
    except Exception as e:
        logger.error(f"Error in camera_stream route: {str(e)}")
        return "Camera stream unavailable", 503

@camera_bp.route('/cameras/discover', methods=['POST'])
@login_required(user_manager)
def discover_cameras():
    """Discover cameras - simplified version."""
    try:
        return jsonify({
            'status': 'maintenance',
            'message': 'Camera discovery is currently under maintenance.',
            'cameras': []
        })
    except Exception as e:
        logger.error(f"Error in discover_cameras route: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@camera_bp.route('/cameras/delete/<camera_id>', methods=['POST'])
@login_required(user_manager)
def delete_camera(camera_id):
    """Delete a camera - simplified version."""
    try:
        flash("Camera functionality is currently under maintenance. Please try again later.", "warning")
        return redirect(url_for('camera.cameras'))
    except Exception as e:
        logger.error(f"Error in delete_camera route: {str(e)}")
        flash("An error occurred while processing your request.", "danger")
        return redirect(url_for('camera.cameras'))

def register_camera_routes(app, detector=None, db_manager_instance=None):
    """Register camera routes with the Flask application."""
    global db_manager
    
    # Store db_manager for later use
    if db_manager_instance is not None:
        db_manager = db_manager_instance
    
    # Initialize camera manager
    init_camera_manager(app.config)
    
    # Register blueprint
    app.register_blueprint(camera_bp)
    
    return app
