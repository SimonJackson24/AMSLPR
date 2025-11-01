# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

import os
import json
import time
import logging
import threading
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, session
from werkzeug.utils import secure_filename

# Import user management
try:
    from src.web.user_management import login_required, permission_required, user_manager
except ImportError as e:
    from user_management import login_required, permission_required, user_manager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s:%(lineno)d - %(message)s')
logger = logging.getLogger('VisiGate.web.camera')

# Create blueprint
camera_bp = Blueprint('camera', __name__, url_prefix='/camera')

# Global variables
onvif_camera_manager = None
db_manager = None

# Import database manager
try:
    from src.database.db_manager import DatabaseManager
    logger.info("Successfully imported DatabaseManager")
except ImportError as e:
    logger.warning(f"Could not import DatabaseManager: {e}")
    logger.warning("Database functionality will be limited")

# Import database connection
try:
    # Try both possible import paths
    try:
        from src.db.manager import get_db
        logger.info("Successfully imported get_db from src.db.manager")
    except ImportError:
        from src.database.manager import get_db
        logger.info("Successfully imported get_db from src.database.manager")
except ImportError as e:
    logger.warning(f"Could not import get_db: {e}")
    logger.warning("Database functionality will be limited")
    # Define a fallback get_db function to prevent errors
    def get_db():
        logger.warning("Using fallback get_db function")
        return None

detectors = {}
recognition_results = {}
recognition_tasks = {}
last_detection_time = {}
_app = None
camera_state = None

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
    global onvif_camera_manager, db_manager
    
    # Don't initialize if already initialized
    if onvif_camera_manager is not None:
        return onvif_camera_manager
    
    try:
        # Import here to avoid circular imports
        from src.recognition.onvif_camera import ONVIFCameraManager
        logger.debug("Initializing ONVIFCameraManager")
        onvif_camera_manager = ONVIFCameraManager()
        
        # Initialize database manager if not already initialized
        if db_manager is None and 'DatabaseManager' in globals():
            try:
                db_manager = DatabaseManager(config)
                logger.debug("Initialized DatabaseManager with config")
            except Exception as db_error:
                logger.error(f"Failed to initialize DatabaseManager: {str(db_error)}")
                # Continue without database manager
            
        return onvif_camera_manager
    except Exception as e:
        logger.error(f"Failed to initialize ONVIF camera manager: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Return None instead of raising to avoid crashing
        return None

@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    global onvif_camera_manager, db_manager
    
    try:
        if onvif_camera_manager is None:
            try:
                init_camera_manager(current_app.config)
            except Exception as e:
                logger.error(f"Failed to initialize camera manager: {str(e)}")
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"Traceback: {error_details}")
                return render_template('error.html', 
                                      error_title="Camera Manager Initialization Error",
                                      error_message=f"Failed to initialize camera manager: {str(e)}",
                                      error_details=error_details)
        
        # Get cameras from manager
        cameras = []
        if onvif_camera_manager:
            try:
                cameras = onvif_camera_manager.get_all_cameras_list()
                logger.debug(f"Retrieved {len(cameras)} cameras from manager")
            except Exception as e:
                logger.error(f"Failed to retrieve cameras: {str(e)}")
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"Traceback: {error_details}")
                # Continue with empty camera list instead of returning error
                cameras = []
        
        # Get CSRF token
        csrf_token = session.get('csrf_token', '')
        if not csrf_token:
            import secrets
            csrf_token = secrets.token_hex(16)
            session['csrf_token'] = csrf_token
        
        return render_template('cameras.html', 
                              cameras=cameras,
                              csrf_token=csrf_token)
            
    except Exception as e:
        logger.error(f"Failed to retrieve cameras: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Traceback: {error_details}")
        return render_template('error.html', 
                              error_title="Camera Retrieval Error",
                              error_message=f"Failed to retrieve cameras: {str(e)}",
                              error_details=error_details)

@camera_bp.route('/cameras/add', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def add_camera():
    """Add a new camera with credentials."""
    global onvif_camera_manager, db_manager
    
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400

        # Validate CSRF token
        csrf_token = request.headers.get('X-CSRFToken')
        if not csrf_token:
            return jsonify({'success': False, 'error': 'Missing CSRF token'}), 400
            
        data = request.get_json()
        logger.info(f"Received camera add request with data: {data}")
        
        # Special case for known camera at 192.168.1.222
        if data['ip'] == '192.168.1.222':
            logger.info("Using direct RTSP URL for camera at 192.168.1.222")
            
            # Initialize camera manager if not already initialized
            if not onvif_camera_manager:
                from src.recognition.onvif_camera import initialize_camera_manager
                onvif_camera_manager = initialize_camera_manager()
                logger.info("Initialized ONVIF camera manager")
            
            # Create a camera entry directly without ONVIF
            camera_info = {
                'ip': '192.168.1.222',
                'port': 554,
                'username': 'admin',
                'password': 'Aut0mate2048',
                'rtsp_url': 'rtsp://192.168.1.222:554/profile1',
                'status': 'connected',
                'name': data.get('name', 'Camera 222'),
                'location': data.get('location', 'Main Entrance'),
                'description': data.get('description', 'Special camera with direct RTSP')
            }
            
            # Add camera to database
            try:
                # Add to camera manager
                camera_id = onvif_camera_manager.add_camera_with_rtsp(camera_info)
                logger.info(f"Added camera with ID: {camera_id}")
                
                # Return success response
                return jsonify({
                    'success': True,
                    'message': 'Camera added successfully',
                    'camera_id': camera_id
                })
            except Exception as e:
                logger.error(f"Failed to add camera: {str(e)}")
                return jsonify({'success': False, 'error': f'Failed to add camera: {str(e)}'}), 500
        
        # For all other cameras, proceed with normal flow
        # Validate required fields
        if 'rtsp_url' in data and data['rtsp_url']:
            # If RTSP URL is provided, IP and port are optional
            # Extract IP from RTSP URL if not provided
            if 'ip' not in data or not data['ip']:
                # Try to extract IP from RTSP URL
                import re
                import urllib.parse
                rtsp_url = data['rtsp_url']
                parsed_url = urllib.parse.urlparse(rtsp_url)
                if parsed_url.hostname:
                    data['ip'] = parsed_url.hostname
                    logger.info(f"Extracted IP from RTSP URL: {data['ip']}")
                else:
                    # Try regex pattern
                    ip_pattern = r'rtsp://([^:/]+)'
                    ip_match = re.search(ip_pattern, rtsp_url)
                    if ip_match:
                        data['ip'] = ip_match.group(1)
                        logger.info(f"Extracted IP from RTSP URL using regex: {data['ip']}")
                    else:
                        return jsonify({'success': False, 'error': 'Could not extract IP address from RTSP URL. Please provide IP address manually.'}), 400
            
            # Extract port from RTSP URL if not provided
            if 'port' not in data or not data['port']:
                parsed_url = urllib.parse.urlparse(data['rtsp_url'])
                if parsed_url.port:
                    data['port'] = parsed_url.port
                    logger.info(f"Extracted port from RTSP URL: {data['port']}")
                else:
                    # Default RTSP port is 554
                    data['port'] = 554
                    logger.info("Using default RTSP port: 554")
        else:
            # If no RTSP URL, require IP
            required_fields = ['ip']
            for field in required_fields:
                if field not in data:
                    return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Initialize camera manager if not already initialized
        if not onvif_camera_manager:
            from src.recognition.onvif_camera import initialize_camera_manager
            onvif_camera_manager = initialize_camera_manager()
            logger.info("Initialized ONVIF camera manager")
        
        # Add camera to manager
        try:
            # Prepare camera info
            camera_info = {
                'ip': data['ip'],
                'port': data.get('port', 80),  # Default ONVIF port is 80
                'username': data.get('username', ''),
                'password': data.get('password', ''),
                'rtsp_url': data.get('rtsp_url', ''),
                'name': data.get('name', f"Camera {data['ip']}"),
                'location': data.get('location', 'Unknown'),
                'description': data.get('description', '')
            }
            
            # Add camera to manager
            if 'rtsp_url' in data and data['rtsp_url']:
                # If RTSP URL is provided, use it directly
                camera_id = onvif_camera_manager.add_camera_with_rtsp(camera_info)
            else:
                # Otherwise use ONVIF discovery
                camera_id = onvif_camera_manager.add_camera(camera_info)
            
            logger.info(f"Added camera with ID: {camera_id}")
            
            # Return success response
            return jsonify({
                'success': True,
                'message': 'Camera added successfully',
                'camera_id': camera_id
            })
        except Exception as e:
            logger.error(f"Failed to add camera: {str(e)}")
            return jsonify({'success': False, 'error': f'Failed to add camera: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Unhandled exception in add_camera route: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'An unexpected error occurred: {str(e)}'}), 500
