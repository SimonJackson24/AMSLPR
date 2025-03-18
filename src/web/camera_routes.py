#!/usr/bin/env python3
"""
Camera routes for the AMSLPR web application.

This module provides routes for managing ONVIF cameras and viewing license plate recognition results.
"""

import os
import cv2
import time
import logging
import threading
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
recognition_threads = {}
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
    """
    Camera management page.
    """
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    cameras = onvif_camera_manager.get_cameras()
    streams = onvif_camera_manager.get_streams()
    
    # Calculate camera stats
    stats = {
        'total': len(cameras),
        'online': 0,
        'offline': 0,
        'issues': 0
    }
    
    # Count online/offline cameras
    for camera in cameras:
        if camera.get('status') == 'online':
            stats['online'] += 1
        else:
            stats['offline'] += 1
    
    return render_template('cameras.html', cameras=cameras, streams=streams, stats=stats)

@camera_bp.route('/cameras/add', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def add_camera():
    """
    Add a new camera.
    """
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
    
    success = onvif_camera_manager.add_camera(
        camera_id=camera_id,
        ip=ip,
        port=port,
        username=username,
        password=password,
        name=name,
        location=location
    )
    
    if success:
        flash(f'Camera {name} added successfully', 'success')
    else:
        flash('Failed to add camera', 'error')
    
    return redirect(url_for('camera.cameras'))

@camera_bp.route('/cameras/remove/<camera_id>', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def remove_camera(camera_id):
    """
    Remove a camera.
    
    Args:
        camera_id (str): ID of the camera to remove
    """
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    # Stop recognition if active
    stop_recognition(camera_id)
    
    success = onvif_camera_manager.remove_camera(camera_id)
    
    return jsonify({'success': success})

@camera_bp.route('/cameras/start/<camera_id>', methods=['POST'])
@login_required(user_manager)
def start_stream(camera_id):
    """
    Start streaming from a camera.
    
    Args:
        camera_id (str): ID of the camera to stream from
    """
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    success = onvif_camera_manager.start_stream(camera_id)
    
    return jsonify({'success': success})

@camera_bp.route('/cameras/stop/<camera_id>', methods=['POST'])
@login_required(user_manager)
def stop_stream(camera_id):
    """
    Stop streaming from a camera.
    
    Args:
        camera_id (str): ID of the camera to stop streaming from
    """
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    # Stop recognition if active
    stop_recognition(camera_id)
    
    success = onvif_camera_manager.stop_stream(camera_id)
    
    return jsonify({'success': success})

@camera_bp.route('/cameras/discover', methods=['POST'])
@login_required(user_manager)
def discover_cameras():
    """
    Discover ONVIF cameras on the network.
    """
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    discovered_cameras = onvif_camera_manager.discover_cameras()
    
    return jsonify({'success': True, 'cameras': discovered_cameras})

@camera_bp.route('/cameras/view/<camera_id>')
@login_required(user_manager)
@permission_required('view', user_manager)
def view_camera(camera_id):
    """
    View a camera.
    
    Args:
        camera_id (str): ID of the camera to view
    """
    global onvif_camera_manager, recognition_results
    
    # Get camera manager
    camera_manager = current_app.config['CAMERA_MANAGER']
    camera = camera_manager.get_camera(camera_id)
    
    if not camera:
        flash(f'Camera {camera_id} not found', 'danger')
        return redirect(url_for('main_dashboard.index'))
    
    # Check if camera is streaming
    stream_active = camera_manager.is_streaming(camera_id)
    recognition_active = camera_manager.is_recognition_active(camera_id)
    
    # Get stream info if active
    stream_info = None
    if stream_active:
        stream_info = camera_manager.get_stream_info(camera_id)
    
    # Get detection area if configured
    detection_area = None
    if 'detection_settings' in camera and 'detection_area' in camera['detection_settings']:
        detection_area = camera['detection_settings']['detection_area']
    
    # Get recent recognition results
    recognition_results = []
    if recognition_active:
        recognition_results = camera_manager.get_recognition_results(camera_id, limit=10)
    
    # Get camera credentials if available
    credentials = None
    if 'encrypted_credentials' in camera:
        try:
            credentials = credential_manager.decrypt_credentials(camera['encrypted_credentials'])
        except Exception as e:
            current_app.logger.error(f"Error decrypting camera credentials: {e}")
    
    return render_template('camera_view.html', 
                           camera=camera, 
                           stream_active=stream_active,
                           recognition_active=recognition_active,
                           stream_info=stream_info,
                           detection_area=detection_area,
                           recognition_results=recognition_results,
                           credentials=credentials)

def generate_frames(camera_id):
    """
    Generate frames from the camera stream.
    
    Args:
        camera_id (str): ID of the camera to stream from
    """
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    while True:
        frame, timestamp = onvif_camera_manager.get_frame(camera_id)
        if frame is None:
            time.sleep(0.1)
            continue
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        
        # Yield the frame in the response
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        # Limit frame rate
        time.sleep(0.03)  # ~30 FPS

@camera_bp.route('/cameras/feed/<camera_id>')
@login_required(user_manager)
def camera_feed(camera_id):
    """
    Stream video feed from a camera.
    
    Args:
        camera_id (str): ID of the camera to stream from
    """
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    return Response(
        generate_frames(camera_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

def recognition_loop(camera_id):
    """
    Recognition loop for a camera.
    
    Args:
        camera_id (str): ID of the camera to recognize plates from
    """
    global onvif_camera_manager, detectors, recognition_results
    if camera_id not in detectors:
        return
    
    detector = detectors[camera_id]
    
    # Initialize results list if not exists
    if camera_id not in recognition_results:
        recognition_results[camera_id] = []
    
    # Get database manager
    db_manager = current_app.config['DB_MANAGER']
    
    # Variables for OCR config reloading
    reload_ocr_config = False
    last_config_check = time.time()
    config_check_interval = 10  # Check for config changes every 10 seconds
    
    while camera_id in detectors:
        try:
            # Check if we need to reload OCR configuration
            current_time = time.time()
            if current_time - last_config_check > config_check_interval:
                last_config_check = current_time
                
                # Check if reload flag is set in the application context
                if hasattr(current_app, 'recognition_reload_config') and current_app.recognition_reload_config:
                    logger.info(f"Reloading OCR configuration for camera {camera_id}...")
                    if detector.reload_ocr_config():
                        logger.info(f"OCR configuration reloaded successfully for camera {camera_id}")
                    else:
                        logger.error(f"Failed to reload OCR configuration for camera {camera_id}")
                    
                    # Reset the flag if this is the last camera
                    if len(detectors) == 1 or camera_id == list(detectors.keys())[-1]:
                        current_app.recognition_reload_config = False
            
            # Process frame
            plate_text = detector.process_frame()
            
            if plate_text:
                # Check if plate is authorized
                authorized = db_manager.is_vehicle_authorized(plate_text)
                
                # Add to results
                recognition_results[camera_id].append({
                    'timestamp': datetime.now(),
                    'plate_text': plate_text,
                    'authorized': authorized
                })
                
                # Limit results list to 20 items
                if len(recognition_results[camera_id]) > 20:
                    recognition_results[camera_id] = recognition_results[camera_id][-20:]
                
                # Log access
                if authorized:
                    db_manager.log_access(plate_text, 'entry', camera_id)
                    logger.info(f"Authorized vehicle {plate_text} detected at camera {camera_id}")
                else:
                    db_manager.log_unauthorized_access(plate_text, camera_id)
                    logger.warning(f"Unauthorized vehicle {plate_text} detected at camera {camera_id}")
                    
                    # Send notification for unauthorized access
                    notification_manager = current_app.config.get('NOTIFICATION_MANAGER')
                    if notification_manager:
                        notification_manager.send_unauthorized_access_notification(
                            plate_text,
                            camera_id,
                            datetime.now()
                        )
            
            # Sleep to avoid excessive CPU usage
            time.sleep(1.0)
        except Exception as e:
            logger.error(f"Error in recognition loop for camera {camera_id}: {e}")
            time.sleep(1.0)

@camera_bp.route('/cameras/recognition/<camera_id>/start', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def start_recognition(camera_id):
    """
    Start license plate recognition for a camera.
    
    Args:
        camera_id (str): ID of the camera to recognize plates from
    """
    global onvif_camera_manager, detectors, recognition_threads
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    # Check if camera exists and is streaming
    camera = onvif_camera_manager.get_camera(camera_id)
    if not camera:
        return jsonify({'success': False, 'error': 'Camera not found'})
    
    streams = onvif_camera_manager.get_streams()
    if camera_id not in streams or not streams[camera_id]['active']:
        return jsonify({'success': False, 'error': 'Camera is not streaming'})
    
    # Check if recognition is already active
    if camera_id in recognition_threads and recognition_threads[camera_id].is_alive():
        return jsonify({'success': True, 'message': 'Recognition already active'})
    
    try:
        # Create detector
        detector_config = {
            'camera_id': camera_id,
            'use_onvif': True,
            'onvif_camera_manager': onvif_camera_manager,
            'save_images': True,
            'image_save_path': os.path.join(current_app.root_path, '..', '..', 'data', 'images', camera_id)
        }
        detectors[camera_id] = LicensePlateDetector(detector_config)
        
        # Start recognition thread
        thread = threading.Thread(target=recognition_loop, args=(camera_id,))
        thread.daemon = True
        thread.start()
        recognition_threads[camera_id] = thread
        
        logger.info(f"Started recognition for camera {camera_id}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error starting recognition for camera {camera_id}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@camera_bp.route('/cameras/recognition/<camera_id>/stop', methods=['POST'])
@login_required(user_manager)
def stop_recognition(camera_id):
    """
    Stop license plate recognition for a camera.
    
    Args:
        camera_id (str): ID of the camera to stop recognition for
    """
    global detectors, recognition_threads
    
    # Check if recognition is active
    if camera_id not in recognition_threads or not recognition_threads[camera_id].is_alive():
        return jsonify({'success': True, 'message': 'Recognition not active'})
    
    try:
        # Stop detector
        if camera_id in detectors:
            detectors[camera_id].cleanup()
            del detectors[camera_id]
        
        # Wait for thread to finish
        recognition_threads[camera_id].join(timeout=5.0)
        del recognition_threads[camera_id]
        
        logger.info(f"Stopped recognition for camera {camera_id}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error stopping recognition for camera {camera_id}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@camera_bp.route('/cameras/snapshot/<camera_id>', methods=['POST'])
@login_required(user_manager)
def capture_snapshot(camera_id):
    """
    Capture a snapshot from a camera.
    
    Args:
        camera_id (str): ID of the camera to capture from
    """
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    # Check if camera exists and is streaming
    camera = onvif_camera_manager.get_camera(camera_id)
    if not camera:
        return jsonify({'success': False, 'error': 'Camera not found'})
    
    streams = onvif_camera_manager.get_streams()
    if camera_id not in streams or not streams[camera_id]['active']:
        return jsonify({'success': False, 'error': 'Camera is not streaming'})
    
    try:
        # Get frame
        frame, timestamp = onvif_camera_manager.get_frame(camera_id)
        if frame is None:
            return jsonify({'success': False, 'error': 'Failed to get frame'})
        
        # Create snapshots directory if it doesn't exist
        snapshots_dir = os.path.join(current_app.root_path, '..', '..', 'data', 'snapshots', camera_id)
        os.makedirs(snapshots_dir, exist_ok=True)
        
        # Save snapshot
        snapshot_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        snapshot_path = os.path.join(snapshots_dir, snapshot_filename)
        cv2.imwrite(snapshot_path, frame)
        
        logger.info(f"Captured snapshot from camera {camera_id}: {snapshot_path}")
        return jsonify({'success': True, 'filename': snapshot_filename})
    except Exception as e:
        logger.error(f"Error capturing snapshot from camera {camera_id}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@camera_bp.route('/cameras/recognition-results/<camera_id>')
@login_required(user_manager)
def get_recognition_results(camera_id):
    """
    Get recognition results for a camera.
    
    Args:
        camera_id (str): ID of the camera to get results for
    """
    global recognition_results
    
    # Get results for this camera
    camera_results = recognition_results.get(camera_id, [])
    
    # Convert to JSON-serializable format
    results_json = []
    for result in camera_results:
        results_json.append({
            'timestamp': result['timestamp'].strftime('%H:%M:%S'),
            'plate_text': result['plate_text'],
            'authorized': result['authorized']
        })
    
    return jsonify({'success': True, 'results': results_json})

@camera_bp.route('/camera/detection-area/<camera_id>', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def save_detection_area(camera_id):
    """Save detection area for a camera."""
    try:
        data = request.json
        points = data.get('points')
        use_detection_area = data.get('use_detection_area', True)
        
        if not points:
            return jsonify({'success': False, 'error': 'No points provided'})
        
        # Get camera manager
        camera_manager = current_app.config['CAMERA_MANAGER']
        camera = camera_manager.get_camera(camera_id)
        
        if not camera:
            return jsonify({'success': False, 'error': f'Camera {camera_id} not found'})
        
        # Update camera detection settings
        if 'detection_settings' not in camera:
            camera['detection_settings'] = {}
        
        camera['detection_settings']['detection_area'] = points
        camera['detection_settings']['use_detection_area'] = use_detection_area
        
        # Save camera configuration
        camera_manager.save_camera_config()
        
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error saving detection area: {e}")
        return jsonify({'success': False, 'error': str(e)})

@camera_bp.route('/settings/<camera_id>', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def save_camera_settings(camera_id):
    """Save camera settings."""
    try:
        settings = request.json
        
        # Get camera manager
        camera_manager = current_app.config['CAMERA_MANAGER']
        camera = camera_manager.get_camera(camera_id)
        
        if not camera:
            return jsonify({'success': False, 'error': f'Camera {camera_id} not found'})
        
        # Update general settings
        camera['name'] = settings.get('name', camera['name'])
        camera['location'] = settings.get('location', camera['location'])
        
        # Handle credentials
        username = settings.get('username')
        password = settings.get('password')
        
        if username and password:
            # Create credentials dictionary
            credentials = {
                'username': username,
                'password': password
            }
            
            # Encrypt credentials
            camera['encrypted_credentials'] = credential_manager.encrypt_credentials(credentials)
        
        # Update detection settings
        if 'detection_settings' not in camera:
            camera['detection_settings'] = {}
        
        camera['detection_settings']['confidence_threshold'] = float(settings.get('confidence_threshold', camera['detection_settings'].get('confidence_threshold', 0.7)))
        camera['detection_settings']['min_plate_size'] = int(settings.get('min_plate_size', camera['detection_settings'].get('min_plate_size', 20)))
        camera['detection_settings']['use_detection_area'] = settings.get('use_detection_area', camera['detection_settings'].get('use_detection_area', False))
        
        # Save camera configuration
        camera_manager.save_camera_config()
        
        # If the camera is streaming, apply the new settings
        if camera_manager.is_streaming(camera_id):
            # Restart the stream to apply new settings
            camera_manager.stop_stream(camera_id)
            camera_manager.start_stream(camera_id)
        
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error saving camera settings: {e}")
        return jsonify({'success': False, 'error': str(e)})

@camera_bp.route('/camera/settings')
@login_required(user_manager)
@permission_required('admin', user_manager)
def camera_settings():
    """
    Camera settings page.
    """
    global onvif_camera_manager
    if onvif_camera_manager is None:
        init_camera_manager(current_app.config)
    
    cameras = onvif_camera_manager.get_cameras()
    
    # Get global camera settings
    settings = {
        'detection_confidence': current_app.config.get('detection_confidence', 0.7),
        'min_plate_size': current_app.config.get('min_plate_size', 20),
        'max_plate_size': current_app.config.get('max_plate_size', 200),
        'recognition_interval': current_app.config.get('recognition_interval', 1.0),
        'save_detections': current_app.config.get('save_detections', True),
        'detection_path': current_app.config.get('detection_path', 'detections'),
    }
    
    return render_template('camera_settings.html', 
                           cameras=cameras, 
                           settings=settings,
                           title="Camera Settings")

@camera_bp.route('/camera/health')
@login_required(user_manager)
def camera_health():
    """
    Display camera health status page.
    """
    # Get camera manager and health monitor
    camera_manager = current_app.config.get('CAMERA_MANAGER')
    health_monitor = current_app.config.get('CAMERA_HEALTH_MONITOR')
    
    if not camera_manager or not health_monitor:
        flash('Camera management system is not available', 'error')
        return redirect(url_for('main_dashboard.index'))
    
    # Get all cameras
    cameras = camera_manager.get_cameras()
    
    # Get health status for all cameras
    health_status = health_monitor.get_camera_health_status()
    
    # Get health summary
    health_summary = health_monitor.get_camera_health_summary()
    
    # Prepare camera data for template
    camera_data = []
    for camera_id, camera in cameras.items():
        # Get stream info if available
        stream_info = camera_manager.get_stream_info(camera_id)
        
        # Prepare camera data
        camera_info = {
            'id': camera_id,
            'name': camera.get('name', 'Unknown'),
            'location': camera.get('location', 'Unknown'),
            'status': health_status.get(camera_id, 'unknown'),
            'last_frame_time': None,
            'fps': None
        }
        
        # Add stream info if available
        if stream_info:
            camera_info['last_frame_time'] = stream_info['last_frame_time'].strftime('%Y-%m-%d %H:%M:%S') if stream_info['last_frame_time'] else None
            camera_info['fps'] = f"{stream_info['fps']:.2f}" if stream_info['fps'] > 0 else None
        
        camera_data.append(camera_info)
    
    # Sort cameras by status (offline first, then stalled, then healthy)
    status_order = {'offline': 0, 'stalled': 1, 'healthy': 2, 'unknown': 3}
    camera_data.sort(key=lambda c: status_order.get(c['status'], 4))
    
    return render_template('camera_health.html', cameras=camera_data, summary=health_summary)

@camera_bp.route('/restart/<camera_id>', methods=['POST'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def restart_camera(camera_id):
    """
    Restart a camera stream.
    """
    # Get camera manager
    camera_manager = current_app.config.get('CAMERA_MANAGER')
    
    if not camera_manager:
        return jsonify({'success': False, 'error': 'Camera management system is not available'})
    
    # Check if camera exists
    camera = camera_manager.get_camera(camera_id)
    if not camera:
        return jsonify({'success': False, 'error': f'Camera {camera_id} not found'})
    
    try:
        # Stop the stream if it's running
        if camera_manager.is_streaming(camera_id):
            camera_manager.stop_stream(camera_id)
        
        # Wait a moment before restarting
        time.sleep(2)
        
        # Start the stream
        success = camera_manager.start_stream(camera_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to start camera stream'})
    except Exception as e:
        current_app.logger.error(f"Error restarting camera {camera_id}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@camera_bp.route('/camera/<camera_id>/detection-area', methods=['GET'])
@login_required(user_manager)
@permission_required('edit', user_manager)
def detection_area_editor(camera_id):
    """Display the detection area editor for a camera."""
    try:
        # Get camera manager
        camera_manager = current_app.config['CAMERA_MANAGER']
        camera = camera_manager.get_camera(camera_id)
        
        if not camera:
            flash(f'Camera {camera_id} not found', 'danger')
            return redirect(url_for('main_dashboard.index'))
        
        # Get detection area if configured
        detection_area = None
        if 'detection_settings' in camera and 'detection_area' in camera['detection_settings']:
            detection_area = camera['detection_settings']['detection_area']
        
        # Take a snapshot for drawing the detection area
        snapshot_path = None
        snapshot_url = None
        
        # Try to get a snapshot from the camera
        try:
            snapshot_result = camera_manager.capture_snapshot(camera_id)
            if snapshot_result and snapshot_result.get('success'):
                snapshot_path = snapshot_result.get('path')
                # Convert absolute path to URL
                if snapshot_path:
                    snapshot_url = f"/static/snapshots/{os.path.basename(snapshot_path)}"
        except Exception as e:
            current_app.logger.error(f"Error capturing snapshot: {e}")
        
        # If we couldn't get a snapshot, use a placeholder image
        if not snapshot_url:
            snapshot_url = "/static/img/camera_placeholder.svg"
        
        return render_template('camera/detection_area.html', 
                               camera=camera,
                               camera_id=camera_id,
                               detection_area=detection_area,
                               snapshot_url=snapshot_url)
    except Exception as e:
        current_app.logger.error(f"Error displaying detection area editor: {e}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('main_dashboard.index'))

def register_camera_routes(app, detector, db_manager):
    """
    Register camera routes with the Flask application.
    
    Args:
        app (Flask): Flask application instance
    """
    setup_routes(app, detector, db_manager)
    app.register_blueprint(camera_bp, url_prefix='')
    
    # Initialize camera manager
    init_camera_manager(app.config)
    
    # Register cleanup function
    @app.teardown_appcontext
    def cleanup(exception=None):
        global onvif_camera_manager, detectors
        
        # Stop all recognition
        for camera_id in list(detectors.keys()):
            try:
                stop_recognition(camera_id)
            except Exception as e:
                logger.error(f"Error stopping recognition for camera {camera_id}: {e}")
        
        # Clean up camera manager
        if onvif_camera_manager is not None:
            onvif_camera_manager.cleanup()
