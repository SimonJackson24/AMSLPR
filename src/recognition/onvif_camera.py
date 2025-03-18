#!/usr/bin/env python3
"""
ONVIF Camera module for connecting to IP cameras using the ONVIF protocol.

This module provides functionality to discover, connect to, and stream from
ONVIF-compatible IP cameras for license plate recognition.
"""

import os
import cv2
import time
import logging
import threading
import numpy as np
from datetime import datetime
from onvif import ONVIFCamera
from urllib.parse import urlparse
from src.utils.security import CredentialManager

logger = logging.getLogger('AMSLPR.recognition.onvif')

class ONVIFCameraManager:
    """
    Class for managing ONVIF-compatible IP cameras.
    Provides functionality to discover, connect to, and stream from IP cameras.
    """
    
    def __init__(self, config):
        """
        Initialize the ONVIF camera manager.
        
        Args:
            config (dict): Configuration dictionary for ONVIF camera
        """
        self.config = config
        self.cameras = {}
        self.streams = {}
        self.running = False
        self.discovery_thread = None
        self.credential_manager = CredentialManager()
        
        # Default configuration values
        self.discovery_enabled = config.get('discovery_enabled', True)
        self.discovery_interval = config.get('discovery_interval', 60)  # seconds
        self.default_username = config.get('default_username', 'admin')
        self.default_password = config.get('default_password', 'admin')
        
        # Initialize pre-configured cameras
        self._init_cameras()
        
        # Start discovery if enabled
        if self.discovery_enabled:
            self.start_discovery()
    
    def _init_cameras(self):
        """
        Initialize pre-configured cameras from config.
        """
        preconfigured_cameras = self.config.get('cameras', [])
        for camera_config in preconfigured_cameras:
            try:
                camera_id = camera_config.get('id')
                if not camera_id:
                    logger.warning("Skipping camera without ID")
                    continue
                
                # Encrypt credentials if present
                if 'username' in camera_config and 'password' in camera_config:
                    credentials = {
                        'username': camera_config['username'],
                        'password': camera_config['password']
                    }
                    
                    # Remove plaintext credentials
                    camera_config.pop('username', None)
                    camera_config.pop('password', None)
                    
                    # Add encrypted credentials
                    camera_config['encrypted_credentials'] = self.credential_manager.encrypt_credentials(credentials)
                
                self.add_camera(
                    camera_id=camera_id,
                    ip=camera_config.get('ip'),
                    port=camera_config.get('port', 80),
                    name=camera_config.get('name', f"Camera {camera_id}"),
                    location=camera_config.get('location', 'Unknown')
                )
            except Exception as e:
                logger.error(f"Error initializing camera {camera_config.get('id')}: {e}")
    
    def start_discovery(self):
        """
        Start the ONVIF camera discovery process in a separate thread.
        """
        if self.discovery_thread is not None and self.discovery_thread.is_alive():
            logger.warning("Discovery already running")
            return
        
        self.running = True
        self.discovery_thread = threading.Thread(target=self._discovery_loop)
        self.discovery_thread.daemon = True
        self.discovery_thread.start()
        logger.info("ONVIF camera discovery started")
    
    def stop_discovery(self):
        """
        Stop the ONVIF camera discovery process.
        """
        self.running = False
        if self.discovery_thread is not None:
            self.discovery_thread.join(timeout=5.0)
            self.discovery_thread = None
        logger.info("ONVIF camera discovery stopped")
    
    def _discovery_loop(self):
        """
        Main loop for discovering ONVIF cameras on the network.
        """
        while self.running:
            try:
                self.discover_cameras()
            except Exception as e:
                logger.error(f"Error in camera discovery: {e}")
            
            # Sleep for the discovery interval
            for _ in range(int(self.discovery_interval)):
                if not self.running:
                    break
                time.sleep(1)
    
    def discover_cameras(self):
        """
        Discover ONVIF cameras on the network.
        
        Returns:
            list: List of discovered camera information
        """
        # This is a placeholder for actual discovery
        # In a real implementation, this would use the ONVIF WS-Discovery protocol
        # For now, we'll just log that discovery is happening
        logger.info("Discovering ONVIF cameras on the network...")
        
        # TODO: Implement actual ONVIF discovery
        # This would involve broadcasting WS-Discovery messages and processing responses
        
        return []
    
    def add_camera(self, camera_id, ip, port=80, name=None, location=None):
        """
        Add a new ONVIF camera to the manager.
        
        Args:
            camera_id (str): Unique identifier for the camera
            ip (str): IP address of the camera
            port (int): Port number for the camera (default: 80)
            name (str): Human-readable name for the camera
            location (str): Physical location of the camera
            
        Returns:
            bool: True if camera was added successfully, False otherwise
        """
        try:
            if camera_id in self.cameras:
                logger.warning(f"Camera with ID {camera_id} already exists")
                return False
            
            # Create ONVIF camera object
            camera = ONVIFCamera(ip, port, self.default_username, self.default_password)
            
            # Get camera information
            device_info = camera.devicemgmt.GetDeviceInformation()
            
            # Get camera media service
            media_service = camera.create_media_service()
            
            # Get camera profiles
            profiles = media_service.GetProfiles()
            
            # Get stream URI for the first profile
            token = profiles[0].token
            stream_setup = {
                'Stream': 'RTP-Unicast',
                'Transport': {
                    'Protocol': 'RTSP'
                }
            }
            stream_uri = media_service.GetStreamUri(stream_setup, token)
            
            # Store camera information
            self.cameras[camera_id] = {
                'id': camera_id,
                'ip': ip,
                'port': port,
                'name': name or f"Camera {camera_id}",
                'location': location or 'Unknown',
                'manufacturer': device_info.Manufacturer,
                'model': device_info.Model,
                'serial_number': device_info.SerialNumber,
                'firmware_version': device_info.FirmwareVersion,
                'profiles': profiles,
                'stream_uri': stream_uri.Uri,
                'onvif_camera': camera,
                'media_service': media_service,
                'added_at': datetime.now()
            }
            
            logger.info(f"Added camera {camera_id} ({ip}:{port})")
            return True
        except Exception as e:
            logger.error(f"Error adding camera {camera_id}: {e}")
            return False
    
    def remove_camera(self, camera_id):
        """
        Remove a camera from the manager.
        
        Args:
            camera_id (str): ID of the camera to remove
            
        Returns:
            bool: True if camera was removed successfully, False otherwise
        """
        if camera_id not in self.cameras:
            logger.warning(f"Camera with ID {camera_id} not found")
            return False
        
        # Stop streaming if active
        self.stop_stream(camera_id)
        
        # Remove camera
        del self.cameras[camera_id]
        logger.info(f"Removed camera {camera_id}")
        return True
    
    def get_camera(self, camera_id):
        """
        Get camera information by ID.
        
        Args:
            camera_id (str): ID of the camera
            
        Returns:
            dict: Camera information or None if not found
        """
        return self.cameras.get(camera_id)
    
    def get_cameras(self):
        """
        Get all cameras.
        
        Returns:
            dict: Dictionary of all cameras
        """
        return self.cameras
    
    def start_stream(self, camera_id):
        """
        Start streaming from a camera.
        
        Args:
            camera_id (str): ID of the camera to stream from
            
        Returns:
            bool: True if stream was started successfully, False otherwise
        """
        if camera_id not in self.cameras:
            logger.warning(f"Camera with ID {camera_id} not found")
            return False
        
        if camera_id in self.streams and self.streams[camera_id]['active']:
            logger.warning(f"Stream for camera {camera_id} already active")
            return True
        
        try:
            camera = self.cameras[camera_id]
            stream_uri = camera['stream_uri']
            
            # Parse URI to add authentication if needed
            parsed_uri = urlparse(stream_uri)
            if not parsed_uri.username and not parsed_uri.password:
                # Add authentication to URI
                auth_uri = f"{parsed_uri.scheme}://{self.default_username}:{self.default_password}@{parsed_uri.netloc}{parsed_uri.path}"
            else:
                auth_uri = stream_uri
            
            # Create OpenCV VideoCapture
            cap = cv2.VideoCapture(auth_uri)
            if not cap.isOpened():
                logger.error(f"Failed to open stream for camera {camera_id}")
                return False
            
            # Store stream information
            self.streams[camera_id] = {
                'active': True,
                'capture': cap,
                'uri': auth_uri,
                'started_at': datetime.now(),
                'frame_count': 0,
                'last_frame': None,
                'last_frame_time': None,
                'lock': threading.Lock(),
                'frames': []
            }
            
            # Start frame fetching thread
            thread = threading.Thread(target=self._fetch_frames, args=(camera_id,))
            thread.daemon = True
            thread.start()
            self.streams[camera_id]['thread'] = thread
            
            logger.info(f"Started stream for camera {camera_id}")
            return True
        except Exception as e:
            logger.error(f"Error starting stream for camera {camera_id}: {e}")
            return False
    
    def stop_stream(self, camera_id):
        """
        Stop streaming from a camera.
        
        Args:
            camera_id (str): ID of the camera to stop streaming from
            
        Returns:
            bool: True if stream was stopped successfully, False otherwise
        """
        if camera_id not in self.streams or not self.streams[camera_id]['active']:
            logger.warning(f"No active stream for camera {camera_id}")
            return False
        
        try:
            # Set active flag to False to stop thread
            self.streams[camera_id]['active'] = False
            
            # Wait for thread to finish
            if 'thread' in self.streams[camera_id]:
                self.streams[camera_id]['thread'].join(timeout=5.0)
            
            # Release capture
            self.streams[camera_id]['capture'].release()
            
            # Update stream information
            self.streams[camera_id]['stopped_at'] = datetime.now()
            
            logger.info(f"Stopped stream for camera {camera_id}")
            return True
        except Exception as e:
            logger.error(f"Error stopping stream for camera {camera_id}: {e}")
            return False
    
    def _fetch_frames(self, camera_id):
        """
        Continuously fetch frames from the camera stream.
        
        Args:
            camera_id (str): ID of the camera to fetch frames from
        """
        if camera_id not in self.streams or not self.streams[camera_id]['active']:
            return
        
        stream = self.streams[camera_id]
        cap = stream['capture']
        
        while stream['active']:
            try:
                # Read frame
                ret, frame = cap.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame from camera {camera_id}")
                    # Try to reconnect
                    time.sleep(1.0)
                    continue
                
                # Update stream information
                stream['frame_count'] += 1
                stream['last_frame'] = frame
                stream['last_frame_time'] = datetime.now()
                
                # Store frame in buffer
                with stream['lock']:
                    stream['frames'].append({
                        'frame': frame,
                        'timestamp': datetime.now()
                    })
                
                # Limit frame rate to avoid excessive CPU usage
                time.sleep(0.03)  # ~30 FPS
            except Exception as e:
                logger.error(f"Error fetching frame from camera {camera_id}: {e}")
                time.sleep(1.0)
    
    def get_frame(self, camera_id):
        """
        Get the latest frame from a camera stream.
        
        Args:
            camera_id (str): ID of the camera
            
        Returns:
            tuple: (frame, timestamp) or (None, None) if no frame is available
        """
        if camera_id not in self.streams or not self.streams[camera_id]['active']:
            return None, None
        
        stream = self.streams[camera_id]
        
        # Get the latest frame
        with stream['lock']:
            if not stream['frames']:
                return None, None
            
            frame = stream['frames'][-1]['frame'].copy()
            timestamp = stream['frames'][-1]['timestamp']
        
        # Apply detection area if configured
        camera = self.get_camera(camera_id)
        if (camera and 'detection_settings' in camera and 
                camera['detection_settings'].get('use_detection_area', False) and 
                'detection_area' in camera['detection_settings']):
            
            # Apply detection area mask
            detection_area = camera['detection_settings']['detection_area']
            frame, _ = self.apply_detection_area(frame, detection_area)
        
        # Apply frame size settings if configured
        if camera and 'detection_settings' in camera:
            frame_width = camera['detection_settings'].get('frame_width')
            frame_height = camera['detection_settings'].get('frame_height')
            
            if frame_width and frame_height:
                frame = cv2.resize(frame, (int(frame_width), int(frame_height)))
        
        return frame, timestamp
    
    def get_stream_info(self, camera_id):
        """
        Get information about a camera stream.
        
        Args:
            camera_id (str): ID of the camera
            
        Returns:
            dict: Stream information or None if not found
        """
        if camera_id not in self.streams or not self.streams[camera_id]['active']:
            return None
        
        stream = self.streams[camera_id]
        
        return {
            'started_at': stream['started_at'],
            'frame_count': stream['frame_count'],
            'last_frame_time': stream['last_frame_time'],
            'fps': self._calculate_fps(camera_id)
        }
    
    def get_streams(self):
        """
        Get all active streams.
        
        Returns:
            dict: Dictionary of all active streams
        """
        return {k: v for k, v in self.streams.items() if v['active']}
    
    def apply_detection_area(self, frame, detection_area):
        """
        Apply a detection area mask to the frame.
        
        Args:
            frame (numpy.ndarray): The frame to apply the mask to
            detection_area (str): String of points in format "x1,y1 x2,y2 x3,y3..."
        
        Returns:
            tuple: (masked_frame, polygon_points)
        """
        if frame is None or detection_area is None:
            return frame, None
        
        try:
            # Parse points
            points_str = detection_area.split()
            points = []
            for point_str in points_str:
                x, y = map(float, point_str.split(','))
                points.append((int(x), int(y)))
            
            if len(points) < 3:
                return frame, None
            
            # Create mask
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            polygon_points = np.array(points, dtype=np.int32)
            cv2.fillPoly(mask, [polygon_points], 255)
            
            # Apply mask
            masked_frame = cv2.bitwise_and(frame, frame, mask=mask)
            
            return masked_frame, polygon_points
        except Exception as e:
            logging.error(f"Error applying detection area: {e}")
            return frame, None
    
    def cleanup(self):
        """
        Clean up resources and stop all streams.
        """
        # Stop discovery
        self.stop_discovery()
        
        # Stop all streams
        for camera_id in list(self.streams.keys()):
            self.stop_stream(camera_id)
        
        logger.info("ONVIF camera manager cleaned up")
    
    def get_last_frame_time(self, camera_id):
        """
        Get the timestamp of the last frame received from a camera.
        
        Args:
            camera_id (str): ID of the camera
        
        Returns:
            datetime: Timestamp of the last frame, or None if no frames received
        """
        if camera_id not in self.streams or not self.streams[camera_id]['active']:
            return None
        
        return self.streams[camera_id]['last_frame_time']

    def should_be_streaming(self, camera_id):
        """
        Check if a camera should be streaming based on configuration.
        
        Args:
            camera_id (str): ID of the camera
        
        Returns:
            bool: True if the camera should be streaming, False otherwise
        """
        camera = self.get_camera(camera_id)
        if not camera:
            return False
        
        # Check if camera is configured to auto-start
        return camera.get('auto_start', False)

    def get_stream_info(self, camera_id):
        """
        Get information about a camera stream.
        
        Args:
            camera_id (str): ID of the camera
        
        Returns:
            dict: Stream information, or None if stream not active
        """
        if camera_id not in self.streams or not self.streams[camera_id]['active']:
            return None
        
        stream = self.streams[camera_id]
        
        return {
            'started_at': stream['started_at'],
            'frame_count': stream['frame_count'],
            'last_frame_time': stream['last_frame_time'],
            'fps': self._calculate_fps(camera_id)
        }

    def _calculate_fps(self, camera_id):
        """
        Calculate the current frames per second for a camera stream.
        
        Args:
            camera_id (str): ID of the camera
        
        Returns:
            float: Frames per second, or 0 if not enough data
        """
        if camera_id not in self.streams or not self.streams[camera_id]['active']:
            return 0.0
        
        stream = self.streams[camera_id]
        
        # Need at least 10 frames and some time elapsed to calculate FPS
        if stream['frame_count'] < 10 or not stream['last_frame_time']:
            return 0.0
        
        # Calculate time elapsed since stream started
        elapsed_seconds = (datetime.now() - stream['started_at']).total_seconds()
        if elapsed_seconds <= 0:
            return 0.0
        
        return stream['frame_count'] / elapsed_seconds

    def get_recognition_results(self, camera_id, limit=10):
        """
        Get recent recognition results for a camera.
        
        Args:
            camera_id (str): ID of the camera
            limit (int): Maximum number of results to return
        
        Returns:
            list: List of recognition results
        """
        # This would normally query a database for results
        # For now, return a placeholder
        return []

    def is_recognition_active(self, camera_id):
        """
        Check if license plate recognition is active for a camera.
        
        Args:
            camera_id (str): ID of the camera
        
        Returns:
            bool: True if recognition is active, False otherwise
        """
        # This would check if recognition is running for the camera
        # For now, return a placeholder
        return False

    def _get_camera_credentials(self, camera):
        """
        Get camera credentials.
        
        Args:
            camera (dict): Camera configuration
            
        Returns:
            tuple: (username, password)
        """
        # Check for encrypted credentials
        if 'encrypted_credentials' in camera:
            try:
                # Decrypt credentials
                credentials = self.credential_manager.decrypt_credentials(camera['encrypted_credentials'])
                return credentials['username'], credentials['password']
            except Exception as e:
                logger.error(f"Error decrypting camera credentials: {e}")
        
        # Fall back to plaintext credentials (for backward compatibility)
        return camera.get('username', ''), camera.get('password', '')

    def connect_camera(self, camera_id):
        """
        Connect to a camera.
        
        Args:
            camera_id (str): ID of the camera
            
        Returns:
            ONVIFCamera: ONVIF camera object, or None if connection failed
        """
        camera = self.get_camera(camera_id)
        if not camera:
            logger.error(f"Camera {camera_id} not found")
            return None
        
        try:
            # Get camera credentials
            username, password = self._get_camera_credentials(camera)
            
            # Connect to camera
            cam = ONVIFCamera(
                camera['ip'],
                camera.get('port', 80),
                username,
                password,
                camera.get('wsdl_path', '')
            )
            
            # Create media service
            media = cam.create_media_service()
            
            # Get camera profiles
            profiles = media.GetProfiles()
            
            # Store camera connection and profiles
            self.cameras[camera_id]['connection'] = {
                'cam': cam,
                'media': media,
                'profiles': profiles
            }
            
            logger.info(f"Connected to camera {camera_id}")
            return cam
        except Exception as e:
            logger.error(f"Error connecting to camera {camera_id}: {e}")
            return None
