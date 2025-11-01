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
    # We'll initialize db_manager later when we have access to the app config
except ImportError as e:
    logger.warning(f"Could not import DatabaseManager: {e}")
    logger.warning("Database functionality will be limited")

# Import database connection - using the correct path
try:
    from src.db.manager import get_db
except ImportError as e:
    logger.warning(f"Could not import get_db: {e}")
    logger.warning("Database functionality will be limited")

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
            db_manager = DatabaseManager(config)
            logger.debug("Initialized DatabaseManager")
            
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
                return render_template('error.html', 
                                      error_title="Camera Retrieval Error",
                                      error_message=f"Failed to retrieve cameras: {str(e)}",
                                      error_details=error_details)
        
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
        
    except Exception as e:
        logger.error(f"Unhandled exception in cameras route: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Traceback: {error_details}")
        return render_template('error.html', 
                              error_title="Camera Page Error",
                              error_message=f"An unexpected error occurred: {str(e)}",
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

@camera_bp.route('/cameras/delete/<camera_id>', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def delete_camera(camera_id):
    """Delete a camera."""
    global onvif_camera_manager
    
    try:
        # Initialize camera manager if not already initialized
        if not onvif_camera_manager:
            init_camera_manager(current_app.config)
        
        # Delete camera
        if onvif_camera_manager:
            result = onvif_camera_manager.delete_camera(camera_id)
            if result:
                flash('Camera deleted successfully', 'success')
            else:
                flash('Failed to delete camera', 'danger')
        else:
            flash('Camera manager not initialized', 'danger')
        
        return redirect(url_for('camera.cameras'))
    except Exception as e:
        logger.error(f"Failed to delete camera: {str(e)}")
        flash(f'Failed to delete camera: {str(e)}', 'danger')
        return redirect(url_for('camera.cameras'))

@camera_bp.route('/cameras/edit/<camera_id>', methods=['GET', 'POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def edit_camera(camera_id):
    """Edit a camera."""
    global onvif_camera_manager
    
    try:
        # Initialize camera manager if not already initialized
        if not onvif_camera_manager:
            init_camera_manager(current_app.config)
        
        # Get camera
        camera = None
        if onvif_camera_manager:
            camera = onvif_camera_manager.get_camera_info(camera_id)
        
        if not camera:
            flash('Camera not found', 'danger')
            return redirect(url_for('camera.cameras'))
        
        if request.method == 'POST':
            # Update camera
            data = request.form.to_dict()
            
            # Prepare camera info
            camera_info = {
                'id': camera_id,
                'name': data.get('name', camera.get('name', '')),
                'location': data.get('location', camera.get('location', '')),
                'description': data.get('description', camera.get('description', '')),
                'username': data.get('username', camera.get('username', '')),
                'password': data.get('password', camera.get('password', '')),
                'rtsp_url': data.get('rtsp_url', camera.get('rtsp_url', ''))
            }
            
            # Update camera
            result = onvif_camera_manager.update_camera(camera_info)
            if result:
                flash('Camera updated successfully', 'success')
            else:
                flash('Failed to update camera', 'danger')
            
            return redirect(url_for('camera.cameras'))
        
        return render_template('camera_edit.html', camera=camera, camera_id=camera_id)
    except Exception as e:
        logger.error(f"Failed to edit camera: {str(e)}")
        flash(f'Failed to edit camera: {str(e)}', 'danger')
        return redirect(url_for('camera.cameras'))

@camera_bp.route('/cameras/stream/<camera_id>')
@login_required(user_manager)
def camera_stream(camera_id):
    """Stream camera feed."""
    global onvif_camera_manager
    
    try:
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
    except Exception as e:
        logger.error(f"Error streaming camera feed: {str(e)}")
        return "Error streaming camera feed", 500

@camera_bp.route('/camera/health')
@login_required(user_manager)
def camera_health():
    """Get camera health status."""
    global onvif_camera_manager
    
    try:
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
    except Exception as e:
        logger.error(f"Error getting camera health: {str(e)}")
        return "Error getting camera health", 500

@camera_bp.route('/camera/view/<camera_id>')
def view_camera(camera_id):
    """View a specific camera."""
    global onvif_camera_manager
    
    try:
        # Get camera from manager
        camera = onvif_camera_manager.get_camera_info(camera_id)
        if not camera:
            flash('Camera not found', 'danger')
            return redirect(url_for('camera.cameras'))
        
        return render_template('camera_view.html', camera=camera, camera_id=camera_id)
    except Exception as e:
        logger.error(f"Error getting camera info: {e}")
        flash(f'Error getting camera info: {str(e)}', 'danger')
        return redirect(url_for('camera.cameras'))

@camera_bp.route('/cameras/discover', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def discover_cameras():
    """Discover cameras on the network."""
    global onvif_camera_manager
    
    try:
        # Initialize camera manager if not already initialized
        if not onvif_camera_manager:
            init_camera_manager(current_app.config)
        
        # Discover cameras
        if onvif_camera_manager:
            discovered_cameras = onvif_camera_manager.discover_cameras()
            return jsonify({
                'success': True,
                'cameras': discovered_cameras
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Camera manager not initialized'
            }), 500
    except Exception as e:
        logger.error(f"Failed to discover cameras: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to discover cameras: {str(e)}'
        }), 500
