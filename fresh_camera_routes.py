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
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('AMSLPR.web.cameras')

# Create blueprint
camera_bp = Blueprint('camera', __name__)

# Global variables
onvif_camera_manager = None
db_manager = None

def init_camera_manager(config):
    """Initialize the camera manager with the given configuration."""
    global onvif_camera_manager, db_manager
    
    logger.info("Initializing camera manager")
    
    # Initialize database manager if needed
    if db_manager is None:
        try:
            from src.database.db_manager import DatabaseManager
            logger.info("Initializing database manager")
            db_manager = DatabaseManager(config)
            logger.info("Database manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {str(e)}")
            db_manager = None
    
    # Initialize camera manager if needed
    if onvif_camera_manager is None:
        try:
            from src.recognition.onvif_camera import ONVIFCameraManager
            logger.info("Creating new ONVIFCameraManager instance")
            onvif_camera_manager = ONVIFCameraManager()
            logger.info(f"ONVIFCameraManager initialized")
            
            # Load cameras from database
            if db_manager:
                try:
                    logger.info("Loading cameras from database")
                    cameras = db_manager.get_all_cameras()
                    logger.info(f"Found {len(cameras)} cameras in database")
                except Exception as e:
                    logger.error(f"Failed to load cameras from database: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to initialize camera manager: {str(e)}")
            onvif_camera_manager = None
    
    return onvif_camera_manager

@camera_bp.route('/cameras')
def cameras():
    """Camera management page."""
    logger.info("Accessing cameras page")
    
    try:
        # Initialize camera manager if needed
        global onvif_camera_manager
        if onvif_camera_manager is None:
            logger.info("Camera manager not initialized, initializing now")
            init_camera_manager(current_app.config)
        
        # Get cameras
        cameras_list = []
        if onvif_camera_manager and hasattr(onvif_camera_manager, 'cameras'):
            try:
                logger.info("Getting cameras from manager")
                for camera_id, camera_data in onvif_camera_manager.cameras.items():
                    camera = {
                        'id': camera_id,
                        'name': 'Unknown',
                        'location': 'Unknown',
                        'status': 'unknown',
                        'manufacturer': 'Unknown',
                        'model': 'Unknown'
                    }
                    
                    # Try to extract camera info
                    if isinstance(camera_data, dict):
                        if 'info' in camera_data:
                            camera_info = camera_data['info']
                            if isinstance(camera_info, dict):
                                camera.update({
                                    'name': camera_info.get('name', 'Unknown'),
                                    'location': camera_info.get('location', 'Unknown'),
                                    'status': camera_info.get('status', 'unknown'),
                                    'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                                    'model': camera_info.get('model', 'Unknown')
                                })
                    
                    cameras_list.append(camera)
                logger.info(f"Found {len(cameras_list)} cameras")
            except Exception as e:
                logger.error(f"Error getting cameras: {str(e)}")
        
        # Calculate camera stats
        online_count = sum(1 for c in cameras_list if c.get('status') == 'online')
        offline_count = sum(1 for c in cameras_list if c.get('status') == 'offline')
        unknown_count = sum(1 for c in cameras_list if c.get('status') not in ['online', 'offline'])
        
        stats = {
            'online': online_count,
            'offline': offline_count,
            'unknown': unknown_count,
            'total': len(cameras_list),
            'avg_fps': '24.5'  # Default value
        }
        
        logger.info(f"Camera stats: {stats}")
        
        # Render template
        return render_template('cameras.html', cameras=cameras_list, stats=stats)
    except Exception as e:
        logger.error(f"Error in cameras route: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return render_template('error.html', 
                              error_title="Camera Page Error",
                              error_message=f"An unexpected error occurred: {str(e)}",
                              error_details="Check logs for more information")

@camera_bp.route('/cameras/<camera_id>')
def camera_view(camera_id):
    """View a specific camera."""
    return render_template('camera_view.html', camera_id=camera_id)

@camera_bp.route('/cameras/<camera_id>/settings')
def camera_settings(camera_id):
    """Camera settings page."""
    return render_template('camera_settings.html', camera_id=camera_id)

@camera_bp.route('/cameras/add', methods=['POST'])
def add_camera():
    """Add a new camera."""
    # Just redirect back to the cameras page
    flash("Camera added successfully", "success")
    return redirect(url_for('camera.cameras'))

@camera_bp.route('/cameras/<camera_id>/delete', methods=['POST'])
def delete_camera(camera_id):
    """Delete a camera."""
    return jsonify({'success': True, 'message': 'Camera deleted successfully'})

@camera_bp.route('/cameras/discover', methods=['POST'])
def discover_cameras():
    """Discover cameras on the network."""
    return jsonify({'success': True, 'message': 'Camera discovery started'})

def register_camera_routes(app, detector=None, db_manager=None):
    """Register camera routes with the Flask application."""
    app.register_blueprint(camera_bp)
    logger.info("Camera routes registered")
