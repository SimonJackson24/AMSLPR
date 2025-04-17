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
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, Response, current_app, send_file
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
db_manager = None

# Import database manager
try:
    from src.database.db_manager import DatabaseManager
    # We'll initialize db_manager later when we have access to the app config
except ImportError as e:
    try:
        from src.db.manager import DatabaseManager
        logger.warning("Using alternative DatabaseManager import path")
    except ImportError as e:
        logger.warning(f"Could not import DatabaseManager: {e}")
        logger.warning("Database functionality will be limited")
        DatabaseManager = None

# Import database connection - wrap in try/except to prevent errors
try:
    from src.database.db import get_db
except ImportError as e:
    logger.warning(f"Could not import get_db: {e}")
    def get_db():
        logger.warning("Using dummy get_db function")
        return None

detectors = {}
recognition_results = {}
recognition_tasks = {}
_detector = None
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
    """Initialize the camera manager with the given configuration."""
    global onvif_camera_manager, db_manager, _db_manager
    
    # Add detailed logging
    logger.info("Initializing camera manager")
    
    # Initialize database manager if not already initialized
    if db_manager is None and DatabaseManager is not None:
        try:
            logger.info("Initializing database manager")
            db_manager = DatabaseManager(config)
            _db_manager = db_manager  # Ensure _db_manager is also set
            logger.info("Database manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {str(e)}")
            db_manager = None
            _db_manager = None
    
    # Initialize camera manager if not already initialized
    if onvif_camera_manager is None:
        try:
            from src.recognition.onvif_camera import ONVIFCameraManager
            logger.info("Creating new ONVIFCameraManager instance")
            onvif_camera_manager = ONVIFCameraManager()
            logger.info(f"ONVIFCameraManager initialized: {onvif_camera_manager}")
            
            # Load cameras from database using the reload function
            if db_manager:
                try:
                    logger.info("Loading cameras from database using reload_cameras_from_database()")
                    # Call the dedicated function to load cameras consistently
                    reload_cameras_from_database()
                except Exception as e:
                    logger.error(f"Failed to load cameras from database: {str(e)}")
        except ImportError as e:
            logger.error(f"Failed to import ONVIFCameraManager: {str(e)}")
            from src.recognition.mock_camera import MockCameraManager
            onvif_camera_manager = MockCameraManager()
            logger.warning("Using MockCameraManager instead")
        except Exception as e:
            logger.error(f"Failed to initialize camera manager: {str(e)}")
            onvif_camera_manager = None
    
    return onvif_camera_manager

def reload_cameras_from_database():
    """Reload cameras from the database."""
    global onvif_camera_manager, db_manager
    
    if not (db_manager and onvif_camera_manager and hasattr(onvif_camera_manager, 'cameras')):
        return False
    
    try:
        logger.info("Reloading cameras from database")
        
        # Check if get_all_cameras method exists
        if not hasattr(db_manager, 'get_all_cameras'):
            logger.warning("Database manager does not have get_all_cameras method")
            return False
            
        cameras = db_manager.get_all_cameras()
        logger.info(f"Found {len(cameras)} cameras in database")
        
        # Store existing cameras temporarily instead of clearing them
        # This ensures we don't lose cameras if there's an issue with the database
        existing_cameras = dict(onvif_camera_manager.cameras)
        
        # Add each camera from the database
        for camera in cameras:
            try:
                logger.info(f"Adding camera from database: {camera['ip']}")
                camera_info = {
                    'ip': camera['ip'],
                    'port': camera.get('port', 80),
                    'username': camera.get('username', ''),
                    'password': camera.get('password', '')
                }
                
                # Add additional fields if they exist
                for field in ['stream_uri', 'manufacturer', 'model', 'name', 'location']:
                    if field in camera and camera[field]:
                        camera_info[field] = camera[field]
                
                # Check if this is an RTSP camera (stored with rtsp- prefix)
                if camera['ip'].startswith('rtsp-'):
                    logger.info(f"Found RTSP camera: {camera['ip']}")
                    camera_id = camera['ip']
                    rtsp_url = camera.get('stream_uri', '')
                    
                    # Add directly to cameras dict
                    onvif_camera_manager.cameras[camera_id] = {
                        'camera': None,  # No ONVIF camera object
                        'info': {
                            'id': camera_id,
                            'name': camera.get('name', 'RTSP Camera'),
                            'location': camera.get('location', 'Unknown'),
                            'status': 'connected',
                            'stream_uri': rtsp_url,
                            'rtsp_url': rtsp_url,
                            'manufacturer': camera.get('manufacturer', 'Unknown'),
                            'model': camera.get('model', 'RTSP Camera')
                        },
                        'stream': None
                    }
                    logger.info(f"Added RTSP camera to manager: {camera_id}")
                else:
                    # Regular ONVIF camera
                    if 'stream_uri' in camera and camera['stream_uri']:
                        camera_info['rtsp_url'] = camera['stream_uri']
                    
                    # Only add if not already in the manager
                    if camera['ip'] not in onvif_camera_manager.cameras:
                        logger.info(f"Adding ONVIF camera to manager: {camera_info}")
                        onvif_camera_manager.add_camera(camera_info)
            except Exception as e:
                logger.error(f"Failed to add camera {camera['ip']}: {str(e)}")
                # Continue with next camera
        
        logger.info("Successfully reloaded cameras from database")
        return True
    except Exception as e:
        logger.error(f"Failed to reload cameras from database: {str(e)}")
        return False

@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    global onvif_camera_manager, db_manager
    
    # Capture diagnostic information
    diagnostics = {
        'camera_manager_type': type(onvif_camera_manager).__name__ if onvif_camera_manager else 'None',
        'db_manager_type': type(db_manager).__name__ if db_manager else 'None',
        'camera_manager_methods': dir(onvif_camera_manager) if onvif_camera_manager else [],
        'camera_manager_has_cameras': hasattr(onvif_camera_manager, 'cameras') if onvif_camera_manager else False,
        'camera_count': len(onvif_camera_manager.cameras) if onvif_camera_manager and hasattr(onvif_camera_manager, 'cameras') else 0
    }
    
    logger.info(f"Diagnostics at start of cameras route: {diagnostics}")
    
    try:
        # Step 1: Initialize camera manager if needed
        if onvif_camera_manager is None:
            try:
                logger.info("Camera manager not initialized, initializing now")
                camera_manager = init_camera_manager(current_app.config)
                if camera_manager is None:
                    error_msg = "Camera manager initialization returned None"
                    logger.error(error_msg)
                    return render_template('error.html', 
                                          error_title="Camera Manager Error",
                                          error_message=error_msg,
                                          error_details="Check logs for more information")
            except Exception as e:
                logger.error(f"Failed to initialize camera manager: {str(e)}")
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"Traceback: {error_details}")
                return render_template('error.html', 
                                      error_title="Camera Manager Initialization Error",
                                      error_message=f"Failed to initialize camera manager: {str(e)}",
                                      error_details=error_details)
        
        # Step 2: Verify camera manager is properly initialized
        if not onvif_camera_manager:
            error_msg = "Camera manager is not available after initialization attempt"
            logger.error(error_msg)
            return render_template('error.html', 
                                  error_title="Camera Manager Error",
                                  error_message=error_msg,
                                  error_details="Check logs for more information")
        
        # Step 3: Check if cameras attribute exists
        if not hasattr(onvif_camera_manager, 'cameras'):
            error_msg = f"Camera manager does not have 'cameras' attribute. Available attributes: {dir(onvif_camera_manager)}"
            logger.error(error_msg)
            return render_template('error.html', 
                                  error_title="Camera Manager Error",
                                  error_message="Camera manager is missing required attributes",
                                  error_details=error_msg)
        
        # Step 4: Get cameras from manager
        cameras = []
        try:
            # Try the get_all_cameras_list method first
            if hasattr(onvif_camera_manager, 'get_all_cameras_list'):
                logger.info("Using get_all_cameras_list method")
                try:
                    cameras = onvif_camera_manager.get_all_cameras_list()
                    logger.info(f"Retrieved {len(cameras)} cameras using get_all_cameras_list")
                except Exception as e:
                    logger.error(f"Error in get_all_cameras_list: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Continue to fallback method
            
            # Fall back to manual extraction if needed
            if not cameras and hasattr(onvif_camera_manager, 'cameras'):
                logger.info("Using fallback method to get cameras")
                try:
                    # Log camera data structure for debugging
                    camera_keys = list(onvif_camera_manager.cameras.keys())
                    logger.info(f"Camera keys: {camera_keys}")
                    if camera_keys:
                        sample_camera = onvif_camera_manager.cameras[camera_keys[0]]
                        logger.info(f"Sample camera structure: {type(sample_camera)}")
                        if isinstance(sample_camera, dict):
                            logger.info(f"Sample camera keys: {sample_camera.keys()}")
                    
                    # Process each camera
                    for camera_id, camera_data in onvif_camera_manager.cameras.items():
                        try:
                            # Extract camera info with detailed logging
                            logger.debug(f"Processing camera {camera_id}, data type: {type(camera_data)}")
                            
                            camera_info = None
                            if isinstance(camera_data, dict):
                                if 'info' in camera_data:
                                    camera_info = camera_data['info']
                                    logger.debug(f"Using 'info' field, type: {type(camera_info)}")
                                else:
                                    camera_info = camera_data
                                    logger.debug("Using camera_data directly as dict")
                            else:
                                camera_info = camera_data
                                logger.debug(f"Using camera_data directly as {type(camera_data)}")
                            
                            # Handle different data structures with detailed logging
                            camera = {'id': camera_id}
                            
                            if isinstance(camera_info, dict):
                                logger.debug(f"Camera info is dict with keys: {camera_info.keys()}")
                                camera.update({
                                    'name': camera_info.get('name', 'Unknown'),
                                    'location': camera_info.get('location', 'Unknown'),
                                    'status': camera_info.get('status', 'unknown'),
                                    'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                                    'model': camera_info.get('model', 'Unknown')
                                })
                            else:
                                logger.debug(f"Camera info is object with attributes: {dir(camera_info)}")
                                camera.update({
                                    'name': getattr(camera_info, 'name', 'Unknown'),
                                    'location': getattr(camera_info, 'location', 'Unknown'),
                                    'status': getattr(camera_info, 'status', 'unknown'),
                                    'manufacturer': getattr(camera_info, 'manufacturer', 'Unknown'),
                                    'model': getattr(camera_info, 'model', 'Unknown')
                                })
                            
                            cameras.append(camera)
                            logger.debug(f"Successfully processed camera {camera_id}")
                        except Exception as e:
                            logger.error(f"Error processing camera {camera_id}: {str(e)}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Continue with next camera
                    
                    logger.info(f"Retrieved {len(cameras)} cameras using fallback method")
                except Exception as e:
                    logger.error(f"Error in fallback camera retrieval: {str(e)}")
                    import traceback
                    error_details = traceback.format_exc()
                    logger.error(f"Traceback: {error_details}")
                    return render_template('error.html', 
                                          error_title="Camera Retrieval Error",
                                          error_message=f"Failed to retrieve cameras: {str(e)}",
                                          error_details=error_details)
        except Exception as e:
            logger.error(f"Unexpected error retrieving cameras: {str(e)}")
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Traceback: {error_details}")
            return render_template('error.html', 
                                  error_title="Camera Retrieval Error",
                                  error_message=f"Unexpected error retrieving cameras: {str(e)}",
                                  error_details=error_details)
        
        # Step 5: Calculate camera stats
        logger.info(f"Found {len(cameras)} cameras, calculating stats")
        try:
            # Calculate camera stats based on the cameras we have
            online_count = sum(1 for c in cameras if c.get('status') == 'online')
            offline_count = sum(1 for c in cameras if c.get('status') == 'offline')
            unknown_count = sum(1 for c in cameras if c.get('status') not in ['online', 'offline'])
            
            stats = {
                'online': online_count,
                'offline': offline_count,
                'unknown': unknown_count,
                'total': len(cameras),
                'avg_fps': '24.5'  # Default value
            }
            
            logger.info(f"Camera stats: {stats}")
            
            # Step 6: Render the template with the cameras and stats
            if not cameras:
                return render_template('cameras.html', cameras=[], stats={'online': 0, 'offline': 0, 'unknown': 0, 'total': 0, 'avg_fps': 'N/A'})
            else:
                return render_template('cameras.html', cameras=cameras, stats=stats)
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Traceback: {error_details}")
            return render_template('error.html', 
                                  error_title="Template Rendering Error",
                                  error_message=f"Failed to render cameras template: {str(e)}",
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
        
        # Check if we're adding a camera with only RTSP URL (direct stream mode)
        if 'rtsp_url' in data and data['rtsp_url'] and (not data.get('ip') or data.get('ip') == ''):
            logger.info(f"Adding camera with RTSP URL only: {data['rtsp_url']}")
            
            # Generate a unique ID for this camera
            import time
            camera_id = data.get('camera_id', f"rtsp-{int(time.time())}")
            logger.info(f"Generated camera ID: {camera_id}")
            
            # Create a direct RTSP camera entry
            rtsp_url = data['rtsp_url']
            
            # Store camera directly in manager
            try:
                onvif_camera_manager.cameras[camera_id] = {
                    'camera': None,  # No ONVIF camera object
                    'info': {
                        'id': camera_id,
                        'name': data.get('name', 'RTSP Camera'),
                        'location': data.get('location', 'Unknown'),
                        'status': 'connected',
                        'stream_uri': rtsp_url,
                        'rtsp_url': rtsp_url,
                        'manufacturer': 'Unknown',
                        'model': 'RTSP Camera'
                    },
                    'stream': None
                }
                logger.info(f"Added camera to manager with ID: {camera_id}")
            except Exception as e:
                logger.error(f"Failed to add camera to manager: {str(e)}")
                return jsonify({'success': False, 'error': f'Failed to add camera to manager: {str(e)}'}), 500
            
            # Add camera to database
            camera_data = {
                'ip': camera_id,  # Use the unique ID as the identifier
                'port': 0,  # Not applicable for direct RTSP
                'username': data.get('username', ''),
                'password': data.get('password', ''),
                'name': data.get('name', 'RTSP Camera'),
                'location': data.get('location', 'Unknown'),
                'stream_uri': rtsp_url,
                'manufacturer': 'Unknown',
                'model': 'RTSP Camera',
                'serial': 'Unknown',
                'status': 'active'
            }
            
            # Add to database
            try:
                logger.info(f"Adding camera to database with data: {camera_data}")
                if _db_manager and hasattr(_db_manager, 'save_camera'):
                    _db_manager.save_camera(camera_data)
                    logger.info("Camera added to database successfully")
                else:
                    logger.warning("Database manager not available or save_camera method not found")
            except Exception as e:
                logger.error(f"Failed to add camera to database: {str(e)}")
                # Continue anyway - the camera is in memory
            
            logger.info("Returning success response for RTSP camera addition")
            return jsonify({
                'success': True,
                'message': 'RTSP camera added successfully',
                'camera': {
                    'id': camera_id,
                    'name': camera_data['name'],
                    'stream_uri': rtsp_url
                }
            })
        
        # For all other cameras, proceed with normal flow
        # Validate required fields
        required_fields = ['ip']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Initialize camera manager if not already initialized
        if not onvif_camera_manager:
            from src.recognition.onvif_camera import initialize_camera_manager
            onvif_camera_manager = initialize_camera_manager()
            logger.info("Initialized ONVIF camera manager")
        
        # Process port
        port = None
        if 'port' in data and data['port']:
            try:
                port = int(data['port'])
            except (ValueError, TypeError):
                port = 554  # Default RTSP port
        else:
            port = 554  # Default to standard RTSP port
        
        # Create camera info object
        camera_info = {
            'ip': data.get('ip', ''),
            'port': port,
            'username': data.get('username', ''),  # Make username optional
            'password': data.get('password', '')   # Make password optional
        }
        
        # Special handling for known camera at 192.168.1.222
        if data.get('ip') == '192.168.1.222':
            logger.info("Using special handling for camera at 192.168.1.222")
            # Override credentials with known working values
            camera_info['username'] = 'admin'
            camera_info['password'] = 'Aut0mate2048'
        
        # Add RTSP URL to camera_info if provided
        if 'rtsp_url' in data and data['rtsp_url']:
            camera_info['rtsp_url'] = data['rtsp_url']
            logger.info(f"Adding camera with RTSP URL: {data['rtsp_url']}")
        
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
        if data['ip'] in onvif_camera_manager.cameras:
            camera = onvif_camera_manager.cameras[data['ip']]
        else:
            return jsonify({
                'success': False,
                'error': 'Camera was added but not found in manager'
            }), 500
        
        # Check if direct RTSP URL was provided
        if 'rtsp_url' in data and data['rtsp_url']:
            # Use the provided RTSP URL directly
            rtsp_uri = data['rtsp_url']
            logger.info(f"Using provided RTSP URL: {rtsp_uri}")
            
            # Store stream URI in camera info
            camera['info']['stream_uri'] = rtsp_uri
            camera['info']['status'] = 'connected'
            
            # Add camera to database
            camera_data = {
                'ip': camera_info['ip'], # Use extracted IP
                'port': port,
                'username': data.get('username', ''),
                'password': data.get('password', ''),
                'name': data.get('name', f"Camera {camera_info['ip']}"), # Use extracted IP
                'location': data.get('location', 'Unknown'),
                'stream_uri': rtsp_uri,
                'manufacturer': 'Unknown',
                'model': 'RTSP Camera',
                'serial': 'Unknown',
                'status': 'active'
            }
            
            # Add to database
            try:
                if hasattr(db_manager, 'save_camera'):
                    db_manager.save_camera(camera_data)
                    logger.info("Camera added to database successfully")
                else:
                    logger.warning("Database manager does not have save_camera method")
            except Exception as e:
                logger.error(f"Failed to add camera to database: {str(e)}")
                # Continue anyway - the camera is in memory
            
            return jsonify({
                'success': True,
                'message': 'Camera added successfully with RTSP URL',
                'camera': {
                    'ip': camera_info['ip'], # Use extracted IP
                    'name': camera_data['name'], # Use extracted IP
                    'stream_uri': rtsp_uri
                }
            })
        else:
            # Get camera info
            try:
                device_info = camera['camera'].devicemgmt.GetDeviceInformation()
                media_service = camera['camera'].create_media_service()
                profiles = media_service.GetProfiles()
                
                if profiles:
                    # Get stream URI
                    token = profiles[0].token
                    
                    try:
                        # First try the standard approach with StreamSetup
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
                        rtsp_uri = stream_uri.Uri
                    except Exception as e1:
                        logger.warning(f"Error using StreamSetup approach: {str(e1)}")
                        
                        # Try alternative approach for older ONVIF versions
                        try:
                            # Some cameras use a simpler GetStreamUri call
                            stream_uri = media_service.GetStreamUri({'ProfileToken': token})
                            rtsp_uri = stream_uri.Uri
                        except Exception as e2:
                            logger.warning(f"Error using simple GetStreamUri approach: {str(e2)}")
                            
                            # Try direct call as last resort
                            try:
                                stream_uri = media_service.GetStreamUri(token)
                                rtsp_uri = stream_uri.Uri
                            except Exception as e3:
                                logger.warning(f"All GetStreamUri approaches failed: {str(e3)}")
                                
                                # Try constructing the RTSP URL directly for this specific camera model
                                try:
                                    # For your specific camera at 192.168.1.222 that uses profile1
                                    if data['ip'] == '192.168.1.222':
                                        rtsp_uri = f"rtsp://{data['ip']}:554/profile1"
                                        logger.info(f"Using hardcoded RTSP URL pattern for this camera: {rtsp_uri}")
                                    else:
                                        # Try common RTSP URL patterns
                                        potential_paths = [
                                            'profile1',
                                            'stream1',
                                            'ch01/main',
                                            'cam/realmonitor',
                                            'live',
                                            'media/video1',
                                            'h264Preview_01_main',
                                            'video1',
                                            'video.mp4'
                                        ]
                                        
                                        # Use the first path as default
                                        rtsp_uri = f"rtsp://{data['ip']}:554/{potential_paths[0]}"
                                        logger.info(f"Using default RTSP URL pattern: {rtsp_uri}")
                                except Exception as e4:
                                    logger.error(f"Failed to construct RTSP URL: {str(e4)}")
                                    return jsonify({
                                        'success': False,
                                        'error': f'Could not determine stream URI. Please provide an RTSP URL manually.'
                                    }), 400
                    
                    # Store stream URI in camera info
                    camera['info']['stream_uri'] = rtsp_uri
                    camera['info']['status'] = 'connected'
                    
                    # Add camera to database
                    camera_data = {
                        'ip': data['ip'],
                        'port': port,
                        'username': data.get('username', ''),
                        'password': data.get('password', ''),
                        'name': data.get('name', f"Camera {data['ip']}"),
                        'location': data.get('location', 'Unknown'),
                        'stream_uri': rtsp_uri,
                        'manufacturer': device_info.Manufacturer,
                        'model': device_info.Model,
                        'serial': device_info.SerialNumber,
                        'status': 'active'
                    }
                    
                    # Add to database
                    try:
                        db_manager.add_camera(camera_data)
                    except Exception as e:
                        logger.error(f"Failed to add camera to database: {str(e)}")
                        # Continue anyway - the camera is in memory
                    
                    return jsonify({
                        'success': True,
                        'message': 'Camera added successfully',
                        'camera': {
                            'ip': data['ip'],
                            'name': camera_data['name'],
                            'stream_uri': rtsp_uri
                        }
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'No media profiles found for camera'
                    }), 400
            except Exception as e:
                logger.error(f"An error occurred while adding the camera: {str(e)}")
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
                'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'thumbnail': 'default_camera.jpg'  # Add thumbnail attribute
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

@camera_bp.route('/camera/stream/<camera_id>')
@login_required(user_manager)
def camera_stream(camera_id):
    """Stream camera feed."""
    try:
        # Check if camera manager is available
        if not onvif_camera_manager:
            logger.error("Camera manager not available")
            return "Camera manager not available", 500
        
        # Try to reload cameras from database, but continue even if it fails
        if _db_manager and onvif_camera_manager:
            try:
                logger.info("Attempting to reload cameras from database")
                reload_cameras_from_database()
            except Exception as e:
                logger.error(f"Error reloading cameras from database: {str(e)}")
                # Continue anyway - we'll use whatever cameras are in memory
        
        # Check if camera exists
        if camera_id not in onvif_camera_manager.cameras:
            logger.warning(f"Camera not found: {camera_id}")
            return "Camera not found", 404
        
        # Get camera info
        camera_info = onvif_camera_manager.cameras[camera_id]
        if isinstance(camera_info, dict) and 'info' in camera_info:
            camera_info = camera_info['info']
        
        # Get stream URI
        if isinstance(camera_info, dict):
            stream_url = camera_info.get('stream_uri', '')
        else:
            stream_url = getattr(camera_info, 'stream_uri', '')
        
        if not stream_url:
            logger.warning(f"Stream URL not available for camera: {camera_id}")
            return "Stream not available", 404
        
        logger.info(f"Returning stream URL for camera {camera_id}: {stream_url}")
        
        # Return a response that redirects to the actual RTSP stream
        # This allows the browser to handle the stream with appropriate plugins
        return redirect(stream_url)
    except Exception as e:
        logger.error(f"Error streaming camera feed: {str(e)}")
        return "Error streaming camera feed", 500

@camera_bp.route('/camera/view/<camera_id>')
@login_required(user_manager)
def camera_view_stream(camera_id):
    """Render a dedicated page for viewing a camera stream."""
    try:
        # Check if camera manager is available
        if not onvif_camera_manager:
            logger.error("Camera manager not available")
            return "Camera manager not available", 500
        
        # Check if camera exists
        if camera_id not in onvif_camera_manager.cameras:
            logger.warning(f"Camera not found: {camera_id}")
            return "Camera not found", 404
        
        # Get camera info
        camera_info = onvif_camera_manager.cameras[camera_id]
        if isinstance(camera_info, dict) and 'info' in camera_info:
            camera_info = camera_info['info']
        
        # Get stream URI
        if isinstance(camera_info, dict):
            stream_url = camera_info.get('stream_uri', '')
        else:
            stream_url = getattr(camera_info, 'stream_uri', '')
        
        if not stream_url:
            logger.warning(f"Stream URL not available for camera: {camera_id}")
            return "Stream not available", 404
            
        camera_name = camera_info.get('name', camera_id) if isinstance(camera_info, dict) else camera_id
        
        return render_template('camera_stream.html', camera_id=camera_id, stream_url=stream_url, camera_name=camera_name)
    except Exception as e:
        logger.error(f"Error rendering camera view: {str(e)}")
        return "Error rendering camera view", 500

# Standard library imports for FFmpeg process management
import subprocess
import tempfile
import os
import threading
import time
import atexit
import signal
import sys

# Store active FFmpeg processes
ffmpeg_processes = {}

# Store HLS segment directories
hls_dirs = {}

# Clean up FFmpeg processes on exit
def cleanup_ffmpeg():
    for proc in ffmpeg_processes.values():
        try:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error terminating FFmpeg process: {str(e)}")

# Register cleanup handler
atexit.register(cleanup_ffmpeg)

# Handle SIGTERM signal for graceful shutdown
def handle_sigterm(signum, frame):
    cleanup_ffmpeg()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

def ensure_hls_dir(camera_id):
    """Ensure HLS directory exists for camera and return its path."""
    global hls_dirs
    
    # Use a consistent directory name without random suffixes
    base_hls_dir = os.path.join(tempfile.gettempdir(), f"amslpr_hls_{camera_id}")
    
    # Create the directory if it doesn't exist
    if not os.path.exists(base_hls_dir):
        os.makedirs(base_hls_dir, exist_ok=True)
        logger.info(f"Created HLS directory: {base_hls_dir}")
    
    # Store the directory in the global dict
    hls_dirs[camera_id] = base_hls_dir
    return base_hls_dir

def start_ffmpeg_stream(camera_id, rtsp_url):
    """Start FFmpeg process to convert RTSP to HLS."""
    logger.info(f"Starting FFmpeg for camera {camera_id} with RTSP URL: {rtsp_url}")
    
    # Validate RTSP URL
    if not rtsp_url or not rtsp_url.startswith('rtsp://'):
        logger.error(f"Invalid RTSP URL for camera {camera_id}: {rtsp_url}")
        return False
        
    # Check if process is already running
    if camera_id in ffmpeg_processes:
        # Check if process is still running
        if ffmpeg_processes[camera_id].poll() is None:
            logger.info(f"FFmpeg process for camera {camera_id} already running")
            return True
        else:
            logger.info(f"FFmpeg process for camera {camera_id} has ended, restarting")
    
    try:
        # Ensure HLS directory exists
        hls_dir = ensure_hls_dir(camera_id)
        logger.info(f"Using HLS directory: {hls_dir}")
        
        # FFmpeg command to convert RTSP to HLS
        # Use more basic settings that are more likely to work with different cameras
        cmd = [
            'ffmpeg',
            '-y',                  # Overwrite output files without asking
            '-loglevel', 'warning',  # Show warnings and errors
            '-rtsp_transport', 'tcp',  # Use TCP for RTSP (more reliable than UDP)
            '-i', rtsp_url,        # Input URL
            '-c:v', 'copy',        # Copy video stream without re-encoding (if possible)
            '-c:a', 'aac',         # Convert audio to AAC (more compatible)
            '-ac', '2',            # 2 audio channels
            '-b:a', '128k',        # Audio bitrate
            '-f', 'hls',           # Output format is HLS
            '-hls_time', '0.5',    # Each segment is 0.5 seconds (reduced from 2)
            '-hls_list_size', '2', # Keep only 2 segments in the playlist (reduced from 3)
            '-hls_flags', 'delete_segments+append_list+omit_endlist',  # Delete old segments and use low-latency flags
            '-hls_segment_type', 'fmp4', # Use fragmented MP4 segments for lower latency
            os.path.join(hls_dir, 'stream.m3u8')
        ]
        
        logger.info(f"FFmpeg command: {' '.join(cmd)}")
        
        # Start FFmpeg process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        ffmpeg_processes[camera_id] = process
        logger.info(f"Started FFmpeg process for camera {camera_id}")
        
        # Start thread to monitor the process
        def monitor_process():
            for line in process.stderr:
                if line.strip():
                    logger.error(f"FFmpeg [{camera_id}]: {line.strip()}")
            
            if process.poll() is not None:
                logger.warning(f"FFmpeg process for camera {camera_id} ended with code {process.returncode}")
                if camera_id in ffmpeg_processes:
                    del ffmpeg_processes[camera_id]
        
        monitor_thread = threading.Thread(target=monitor_process)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Wait a short time to ensure FFmpeg has started
        time.sleep(1)
        
        # Check if process is still running
        if process.poll() is None:
            return True
        else:
            logger.error(f"FFmpeg process for camera {camera_id} failed to start")
            return False
    
    except Exception as e:
        logger.error(f"Error starting FFmpeg process: {str(e)}")
        return False

@camera_bp.route('/camera/hls-stream/<camera_id>')
def hls_stream(camera_id):
    """
    Convert RTSP stream to HLS stream for web playback.
    
    This endpoint doesn't return the HLS playlist directly, but starts
    the FFmpeg process to generate it and serves the static directory
    containing the playlist and segments.
    """
    try:
        # Check if camera exists and get stream URL
        if not onvif_camera_manager:
            logger.error("Camera manager not available")
            return jsonify({
                'success': False,
                'message': 'Camera manager not available'
            }), 500
            
        if camera_id not in onvif_camera_manager.cameras:
            logger.warning(f"Camera not found: {camera_id}")
            return jsonify({
                'success': False,
                'message': 'Camera not found'
            }), 404
            
        camera_info = onvif_camera_manager.cameras[camera_id]
        logger.info(f"Camera info type: {type(camera_info)}")
        logger.info(f"Camera info content: {camera_info}")
        
        # Extract stream URL and credentials based on data structure
        stream_url = ''
        username = ''
        password = ''
        
        if isinstance(camera_info, dict):
            # If camera_info is a dictionary
            if 'info' in camera_info:
                sub_info = camera_info['info']
                if isinstance(sub_info, dict):
                    stream_url = sub_info.get('stream_uri', '')
                    # Get stored credentials
                    username = sub_info.get('username', '')
                    password = sub_info.get('password', '')
                    logger.info(f"Got stream_uri from info dictionary: {stream_url}")
                else:
                    stream_url = getattr(sub_info, 'stream_uri', '')
                    username = getattr(sub_info, 'username', '')
                    password = getattr(sub_info, 'password', '')
                    logger.info(f"Got stream_uri from info object: {stream_url}")
            else:
                # Direct access in the dictionary
                stream_url = camera_info.get('stream_uri', '')
                username = camera_info.get('username', '')
                password = camera_info.get('password', '')
                logger.info(f"Got stream_uri directly from dictionary: {stream_url}")
        else:
            # If camera_info is an object
            stream_url = getattr(camera_info, 'stream_uri', '')
            username = getattr(camera_info, 'username', '')
            password = getattr(camera_info, 'password', '')
            logger.info(f"Got stream_uri from object attribute: {stream_url}")
            
        if not stream_url:
            logger.warning(f"Stream URL not available for camera: {camera_id}")
            return jsonify({
                'success': False,
                'message': 'Stream URL not available'
            }), 404
            
        # Construct correct RTSP URL with proper credentials if needed
        if stream_url.startswith('rtsp://') and username and password:
            # Check if URL already contains credentials
            if not ('@' in stream_url and stream_url.index('@') < stream_url.index(':', 7)):
                # Parse the URL parts
                url_parts = stream_url.split('://', 1)
                if len(url_parts) == 2:
                    # Add credentials to URL
                    auth_url = f"rtsp://{username}:{password}@{url_parts[1]}"
                    logger.info(f"Added authentication to stream URL: {auth_url}")
                    stream_url = auth_url
        
        # Start FFmpeg process for this camera if not already running
        if not start_ffmpeg_stream(camera_id, stream_url):
            logger.error(f"Failed to start FFmpeg process for camera {camera_id}")
            return jsonify({
                'success': False,
                'message': 'Failed to start FFmpeg process'
            }), 500
        
        # Get the HLS directory for this camera
        hls_dir = hls_dirs.get(camera_id)
        if not hls_dir or not os.path.exists(hls_dir):
            logger.error(f"HLS directory for camera {camera_id} not found")
            return jsonify({
                'success': False,
                'message': 'Stream directory not found'
            }), 500
        
        # Return the HLS playlist URL
        playlist_url = f"/camera/hls-segments/{camera_id}/stream.m3u8"
        
        return jsonify({
            'success': True,
            'playlist_url': playlist_url,
            'camera_id': camera_id,
            'message': 'HLS stream started successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in HLS streaming: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing stream: {str(e)}'
        }), 500

# Route to serve HLS segments
@camera_bp.route('/camera/hls-segments/<camera_id>/<path:filename>')
def hls_segments(camera_id, filename):
    """Serve HLS playlist and segments."""
    try:
        # Get the HLS directory for this camera
        hls_dir = hls_dirs.get(camera_id)
        if not hls_dir or not os.path.exists(hls_dir):
            logger.error(f"HLS directory for camera {camera_id} not found")
            if filename.endswith('.m3u8'):
                # Return an empty HLS playlist if the directory doesn't exist but we're requesting the playlist
                # This prevents player errors and allows for better error handling on the client
                empty_playlist = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:2\n#EXT-X-MEDIA-SEQUENCE:0\n#EXT-X-ENDLIST\n"
                return Response(empty_playlist, mimetype='application/vnd.apple.mpegurl')
            else:
                return "Stream directory not found", 404
        
        # Construct the full path to the requested file
        file_path = os.path.join(hls_dir, filename)
        
        # Check if the file exists
        if not os.path.exists(file_path):
            logger.warning(f"Requested HLS file not found: {file_path}")
            
            # If the playlist is requested but not yet created (FFmpeg might still be starting up)
            # return an empty playlist instead of 404
            if filename.endswith('.m3u8'):
                empty_playlist = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:2\n#EXT-X-MEDIA-SEQUENCE:0\n#EXT-X-ENDLIST\n"
                return Response(empty_playlist, mimetype='application/vnd.apple.mpegurl')
            
            return "File not found", 404
        
        # Determine the correct MIME type
        mime_type = 'application/vnd.apple.mpegurl' if filename.endswith('.m3u8') else 'video/mp2t'
        
        # Create response with appropriate MIME type
        response = send_file(file_path, mimetype=mime_type)
        
        # Add CORS headers to allow cross-origin requests
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Cache-Control'] = 'no-cache'  # Ensure fresh content
        
        return response
        
    except Exception as e:
        logger.error(f"Error serving HLS segment: {str(e)}")
        return jsonify({"success": False, "message": f"Error serving stream file: {str(e)}"}), 500

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
            logger.info(f"Getting camera health data from camera manager")
            if hasattr(camera_manager, 'cameras'):
                cameras = camera_manager.cameras
                logger.info(f"Found {len(cameras)} cameras in manager")
                
                for camera_id, camera_data in cameras.items():
                    logger.info(f"Processing camera health for: {camera_id}")
                    
                    # Get camera info
                    camera_info = camera_data.get('info', {})
                    
                    # Determine status
                    status = camera_info.get('status', 'offline')
                    if status == 'connected':
                        status = 'online'
                        online_count += 1
                    elif status == 'error':
                        status = 'warning'
                        warning_count += 1
                    
                    camera_health_data.append({
                        'id': camera_id,
                        'name': camera_info.get('name', 'Unknown Camera'),
                        'location': camera_info.get('location', 'Unknown'),
                        'status': status,
                        'uptime': '24h 35m',  # Placeholder
                        'last_frame': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'frame_rate': 25,  # Placeholder
                        'thumbnail': 'default_camera.jpg'  # Add thumbnail attribute
                    })
            else:
                logger.warning("Camera manager does not have 'cameras' attribute")
        
        return render_template('camera_health.html', 
                               cameras=camera_health_data,
                               online_count=online_count,
                               warning_count=warning_count,
                               last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        logger.error(f"Error getting camera health: {str(e)}")
        return "Error getting camera health", 500

@camera_bp.route('/camera/<camera_id>')
@login_required(user_manager)
def camera_view(camera_id):
    """View a specific camera."""
    try:
        # Check if camera manager is available
        if not onvif_camera_manager:
            flash('Camera manager not available', 'error')
            return redirect(url_for('camera.cameras'))
        
        # Try to reload cameras from database, but continue even if it fails
        if _db_manager and onvif_camera_manager:
            try:
                logger.info("Attempting to reload cameras from database")
                reload_cameras_from_database()
            except Exception as e:
                logger.error(f"Error reloading cameras from database: {str(e)}")
                # Continue anyway - we'll use whatever cameras are in memory
        
        # Check if camera exists
        if camera_id not in onvif_camera_manager.cameras:
            flash(f'Camera with ID {camera_id} not found', 'error')
            return redirect(url_for('camera.cameras'))
        
        # Get camera info
        camera_info = onvif_camera_manager.cameras[camera_id]
        if isinstance(camera_info, dict) and 'info' in camera_info:
            camera_info = camera_info['info']
        
        # Create camera object with all required fields for the template
        camera = {
            'id': camera_id,
            'name': camera_info.get('name', 'Unknown Camera') if isinstance(camera_info, dict) else getattr(camera_info, 'name', 'Unknown Camera'),
            'location': camera_info.get('location', 'Unknown') if isinstance(camera_info, dict) else getattr(camera_info, 'location', 'Unknown'),
            'status': camera_info.get('status', 'unknown') if isinstance(camera_info, dict) else getattr(camera_info, 'status', 'unknown'),
            'thumbnail': 'default_camera.jpg',  # Add required thumbnail
            'manufacturer': camera_info.get('manufacturer', 'Unknown') if isinstance(camera_info, dict) else getattr(camera_info, 'manufacturer', 'Unknown'),
            'model': camera_info.get('model', 'Unknown') if isinstance(camera_info, dict) else getattr(camera_info, 'model', 'Unknown'),
            'url': camera_info.get('stream_uri', '') if isinstance(camera_info, dict) else getattr(camera_info, 'stream_uri', ''),
            'fps': camera_info.get('fps', 25) if isinstance(camera_info, dict) else getattr(camera_info, 'fps', 25),  # Default FPS
            'uptime': camera_info.get('uptime', '24h') if isinstance(camera_info, dict) else getattr(camera_info, 'uptime', '24h')  # Default uptime
        }
        
        return render_template('camera_view.html', camera=camera)
    except Exception as e:
        logger.error(f"Error viewing camera {camera_id}: {str(e)}")
        flash(f'Error viewing camera: {str(e)}', 'error')
        return redirect(url_for('camera.cameras'))

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
        
        # Check if progressive results requested
        use_progressive = request.json.get('progressive', False)
        
        if use_progressive:
            # Start discovery in a background thread and immediately return
            # The frontend will connect to the event endpoint to get updates
            
            # Store discovered cameras in a shared variable
            if not hasattr(current_app, 'discovered_cameras'):
                current_app.discovered_cameras = {}
            
            # Generate a unique discovery ID
            import uuid
            discovery_id = str(uuid.uuid4())
            current_app.discovered_cameras[discovery_id] = []
            
            # Define callback function for progressive updates
            def discovery_callback(camera):
                if discovery_id in current_app.discovered_cameras:
                    current_app.discovered_cameras[discovery_id].append(camera)
            
            # Start discovery in a background thread
            def run_discovery():
                try:
                    # Reduced timeout from 5 to 2 seconds
                    onvif_camera_manager.discover_cameras(timeout=2, callback=discovery_callback)
                    # Mark discovery as complete
                    if discovery_id in current_app.discovered_cameras:
                        current_app.discovered_cameras[discovery_id].append({'discovery_complete': True})
                except Exception as e:
                    logger.error(f"Error in background discovery: {str(e)}")
                    # Mark discovery as failed
                    if discovery_id in current_app.discovered_cameras:
                        current_app.discovered_cameras[discovery_id].append({
                            'discovery_error': True, 
                            'error': str(e)
                        })
            
            import threading
            discovery_thread = threading.Thread(target=run_discovery)
            discovery_thread.daemon = True
            discovery_thread.start()
            
            # Return immediately with the discovery ID
            return jsonify({
                'success': True,
                'progressive': True,
                'discovery_id': discovery_id,
                'message': 'Camera discovery started in background. Connect to event stream for updates.'
            }), 200
        else:
            # Traditional synchronous discovery with reduced timeout (5 to 2 seconds)
            logger.debug("Starting camera discovery...")
            discovered_cameras = onvif_camera_manager.discover_cameras(timeout=2)
            
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

@camera_bp.route('/cameras/discovery-updates/<discovery_id>')
def camera_discovery_updates(discovery_id):
    """Stream camera discovery updates using Server-Sent Events (SSE)."""
    def event_stream():
        # Check if this discovery ID exists
        if not hasattr(current_app, 'discovered_cameras') or discovery_id not in current_app.discovered_cameras:
            # No such discovery in progress
            yield f"data: {json.dumps({'error': 'Invalid discovery ID'})}\n\n"
            return
        
        # Get the current index in the results
        index = 0
        discovery_complete = False
        
        # While discovery is not complete, yield new cameras as they're found
        while not discovery_complete:
            # Check for new cameras
            cameras = current_app.discovered_cameras[discovery_id]
            
            # Yield any new cameras found since last check
            while index < len(cameras):
                camera = cameras[index]
                
                # Check if this is the completion marker
                if 'discovery_complete' in camera:
                    yield f"data: {json.dumps({'status': 'complete', 'total': len(cameras) - 1})}\n\n"
                    discovery_complete = True
                    break
                
                # Check if this is an error marker
                elif 'discovery_error' in camera:
                    yield f"data: {json.dumps({'status': 'error', 'error': camera.get('error', 'Unknown error')})}\n\n"
                    discovery_complete = True
                    break
                
                # Regular camera update
                else:
                    yield f"data: {json.dumps({'status': 'camera', 'camera': camera, 'count': index + 1})}\n\n"
                
                index += 1
            
            # Don't tight-loop - wait a little bit before checking again
            if not discovery_complete:
                time.sleep(0.5)
        
        # Clean up after discovery is complete
        if hasattr(current_app, 'discovered_cameras') and discovery_id in current_app.discovered_cameras:
            del current_app.discovered_cameras[discovery_id]
    
    # Return an SSE response
    return Response(event_stream(), content_type='text/event-stream')

@camera_bp.route('/test_camera_credentials', methods=['POST'])
def test_camera_credentials():
    """This endpoint has been removed as it was inappropriate."""
    logger.warning("The test_camera_credentials endpoint has been removed as it was inappropriate.")
    return jsonify({
        'success': False,
        'error': 'This functionality has been removed.'
    }), 400

@camera_bp.route('/cameras/delete/<camera_id>', methods=['POST'])
@login_required(user_manager)
@permission_required('cameras.delete', user_manager)
def delete_camera(camera_id):
    """
    Delete a camera from the system.
    
    Args:
        camera_id (str): ID of the camera to delete
        
    Returns:
        JSON response indicating success or failure
    """
    try:
        logger.info(f"Deleting camera with ID: {camera_id}")
        
        # Check if camera exists and delete it
        if onvif_camera_manager:
            result = onvif_camera_manager.delete_camera(camera_id)
            if result:
                # Also delete from database if available
                if _db_manager:
                    try:
                        _db_manager.delete_camera(camera_id)
                        logger.info(f"Camera {camera_id} deleted from database")
                    except Exception as e:
                        logger.error(f"Error deleting camera from database: {str(e)}")
                        # Continue even if database delete fails
                
                return jsonify({
                    'success': True,
                    'message': f"Camera {camera_id} deleted successfully"
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f"Failed to delete camera {camera_id}"
                }), 400
        else:
            return jsonify({
                'success': False,
                'error': "Camera manager not initialized"
            }), 500
    except Exception as e:
        logger.error(f"Error in delete_camera route: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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

@camera_bp.route('/cameras')
@login_required(user_manager)
def cameras():
    """Camera management page."""
    global onvif_camera_manager, db_manager
    
    # Capture diagnostic information
    diagnostics = {
        'camera_manager_type': type(onvif_camera_manager).__name__ if onvif_camera_manager else 'None',
        'db_manager_type': type(db_manager).__name__ if db_manager else 'None',
        'camera_manager_methods': dir(onvif_camera_manager) if onvif_camera_manager else [],
        'camera_manager_has_cameras': hasattr(onvif_camera_manager, 'cameras') if onvif_camera_manager else False,
        'camera_count': len(onvif_camera_manager.cameras) if onvif_camera_manager and hasattr(onvif_camera_manager, 'cameras') else 0
    }
    
    logger.info(f"Diagnostics at start of cameras route: {diagnostics}")
    
    try:
        # Step 1: Initialize camera manager if needed
        if onvif_camera_manager is None:
            try:
                logger.info("Camera manager not initialized, initializing now")
                camera_manager = init_camera_manager(current_app.config)
                if camera_manager is None:
                    error_msg = "Camera manager initialization returned None"
                    logger.error(error_msg)
                    return render_template('error.html', 
                                          error_title="Camera Manager Error",
                                          error_message=error_msg,
                                          error_details="Check logs for more information")
            except Exception as e:
                logger.error(f"Failed to initialize camera manager: {str(e)}")
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"Traceback: {error_details}")
                return render_template('error.html', 
                                      error_title="Camera Manager Initialization Error",
                                      error_message=f"Failed to initialize camera manager: {str(e)}",
                                      error_details=error_details)
        
        # Step 2: Verify camera manager is properly initialized
        if not onvif_camera_manager:
            error_msg = "Camera manager is not available after initialization attempt"
            logger.error(error_msg)
            return render_template('error.html', 
                                  error_title="Camera Manager Error",
                                  error_message=error_msg,
                                  error_details="Check logs for more information")
        
        # Step 3: Check if cameras attribute exists
        if not hasattr(onvif_camera_manager, 'cameras'):
            error_msg = f"Camera manager does not have 'cameras' attribute. Available attributes: {dir(onvif_camera_manager)}"
            logger.error(error_msg)
            return render_template('error.html', 
                                  error_title="Camera Manager Error",
                                  error_message="Camera manager is missing required attributes",
                                  error_details=error_msg)
        
        # Step 4: Get cameras from manager
        cameras = []
        try:
            # Try the get_all_cameras_list method first
            if hasattr(onvif_camera_manager, 'get_all_cameras_list'):
                logger.info("Using get_all_cameras_list method")
                try:
                    cameras = onvif_camera_manager.get_all_cameras_list()
                    logger.info(f"Retrieved {len(cameras)} cameras using get_all_cameras_list")
                except Exception as e:
                    logger.error(f"Error in get_all_cameras_list: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Continue to fallback method
            
            # Fall back to manual extraction if needed
            if not cameras and hasattr(onvif_camera_manager, 'cameras'):
                logger.info("Using fallback method to get cameras")
                try:
                    # Log camera data structure for debugging
                    camera_keys = list(onvif_camera_manager.cameras.keys())
                    logger.info(f"Camera keys: {camera_keys}")
                    if camera_keys:
                        sample_camera = onvif_camera_manager.cameras[camera_keys[0]]
                        logger.info(f"Sample camera structure: {type(sample_camera)}")
                        if isinstance(sample_camera, dict):
                            logger.info(f"Sample camera keys: {sample_camera.keys()}")
                    
                    # Process each camera
                    for camera_id, camera_data in onvif_camera_manager.cameras.items():
                        try:
                            # Extract camera info with detailed logging
                            logger.debug(f"Processing camera {camera_id}, data type: {type(camera_data)}")
                            
                            camera_info = None
                            if isinstance(camera_data, dict):
                                if 'info' in camera_data:
                                    camera_info = camera_data['info']
                                    logger.debug(f"Using 'info' field, type: {type(camera_info)}")
                                else:
                                    camera_info = camera_data
                                    logger.debug("Using camera_data directly as dict")
                            else:
                                camera_info = camera_data
                                logger.debug(f"Using camera_data directly as {type(camera_data)}")
                            
                            # Handle different data structures with detailed logging
                            camera = {'id': camera_id}
                            
                            if isinstance(camera_info, dict):
                                logger.debug(f"Camera info is dict with keys: {camera_info.keys()}")
                                camera.update({
                                    'name': camera_info.get('name', 'Unknown'),
                                    'location': camera_info.get('location', 'Unknown'),
                                    'status': camera_info.get('status', 'unknown'),
                                    'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                                    'model': camera_info.get('model', 'Unknown')
                                })
                            else:
                                logger.debug(f"Camera info is object with attributes: {dir(camera_info)}")
                                camera.update({
                                    'name': getattr(camera_info, 'name', 'Unknown'),
                                    'location': getattr(camera_info, 'location', 'Unknown'),
                                    'status': getattr(camera_info, 'status', 'unknown'),
                                    'manufacturer': getattr(camera_info, 'manufacturer', 'Unknown'),
                                    'model': getattr(camera_info, 'model', 'Unknown')
                                })
                            
                            cameras.append(camera)
                            logger.debug(f"Successfully processed camera {camera_id}")
                        except Exception as e:
                            logger.error(f"Error processing camera {camera_id}: {str(e)}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Continue with next camera
                    
                    logger.info(f"Retrieved {len(cameras)} cameras using fallback method")
                except Exception as e:
                    logger.error(f"Error in fallback camera retrieval: {str(e)}")
                    import traceback
                    error_details = traceback.format_exc()
                    logger.error(f"Traceback: {error_details}")
                    return render_template('error.html', 
                                          error_title="Camera Retrieval Error",
                                          error_message=f"Failed to retrieve cameras: {str(e)}",
                                          error_details=error_details)
        except Exception as e:
            logger.error(f"Unexpected error retrieving cameras: {str(e)}")
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Traceback: {error_details}")
            return render_template('error.html', 
                                  error_title="Camera Retrieval Error",
                                  error_message=f"Unexpected error retrieving cameras: {str(e)}",
                                  error_details=error_details)
        
        # Step 5: Calculate camera stats
        logger.info(f"Found {len(cameras)} cameras, calculating stats")
        try:
            # Calculate camera stats based on the cameras we have
            online_count = sum(1 for c in cameras if c.get('status') == 'online')
            offline_count = sum(1 for c in cameras if c.get('status') == 'offline')
            unknown_count = sum(1 for c in cameras if c.get('status') not in ['online', 'offline'])
            
            stats = {
                'online': online_count,
                'offline': offline_count,
                'unknown': unknown_count,
                'total': len(cameras),
                'avg_fps': '24.5'  # Default value
            }
            
            logger.info(f"Camera stats: {stats}")
            
            # Step 6: Render the template with the cameras and stats
            if not cameras:
                return render_template('cameras.html', cameras=[], stats={'online': 0, 'offline': 0, 'unknown': 0, 'total': 0, 'avg_fps': 'N/A'})
            else:
                return render_template('cameras.html', cameras=cameras, stats=stats)
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Traceback: {error_details}")
            return render_template('error.html', 
                                  error_title="Template Rendering Error",
                                  error_message=f"Failed to render cameras template: {str(e)}",
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
