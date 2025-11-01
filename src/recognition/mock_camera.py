#!/usr/bin/env python3
"""
Mock Camera Manager for testing and fallback when ONVIF cameras are unavailable.

This module provides a mock implementation of the camera manager that can be used
for testing or when real ONVIF cameras are not available.
"""

import logging
import time
import cv2
import numpy as np
from datetime import datetime

logger = logging.getLogger('VisiGate.recognition.mock_camera')

class MockCameraManager:
    """
    Mock implementation of ONVIFCameraManager for testing and fallback.
    """

    def __init__(self):
        """Initialize the mock camera manager."""
        self.cameras = {}
        logger.info("Mock Camera Manager initialized")

        # Add some mock cameras for testing
        self._add_mock_cameras()

    def _add_mock_cameras(self):
        """Add mock cameras for testing purposes."""
        mock_cameras = [
            {
                'ip': 'mock-camera-1',
                'name': 'Mock Camera 1',
                'location': 'Test Location 1',
                'manufacturer': 'Mock Manufacturer',
                'model': 'Mock Model 1',
                'status': 'connected',
                'stream_uri': 'rtsp://mock-camera-1:554/stream'
            },
            {
                'ip': 'mock-camera-2',
                'name': 'Mock Camera 2',
                'location': 'Test Location 2',
                'manufacturer': 'Mock Manufacturer',
                'model': 'Mock Model 2',
                'status': 'connected',
                'stream_uri': 'rtsp://mock-camera-2:554/stream'
            }
        ]

        for camera in mock_cameras:
            self.cameras[camera['ip']] = {
                'camera': None,  # No real ONVIF camera object
                'info': camera,
                'stream': None
            }

        logger.info(f"Added {len(mock_cameras)} mock cameras")

    def get_all_cameras(self):
        """Get all mock cameras."""
        return self.cameras

    def get_all_cameras_list(self):
        """Get all mock cameras as a list."""
        cameras_list = []
        for camera_id, camera_data in self.cameras.items():
            camera_info = camera_data['info']
            cameras_list.append({
                'id': camera_id,
                'name': camera_info.get('name', 'Unknown'),
                'location': camera_info.get('location', 'Unknown'),
                'status': camera_info.get('status', 'unknown'),
                'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                'model': camera_info.get('model', 'Unknown')
            })
        return cameras_list

    def discover_cameras(self, timeout=2):
        """Mock camera discovery - returns mock cameras."""
        logger.info("Mock camera discovery - returning mock cameras")
        discovered = []
        for camera_id, camera_data in self.cameras.items():
            camera_info = camera_data['info'].copy()
            camera_info['type'] = 'Mock Camera'
            camera_info['requires_auth'] = False
            discovered.append(camera_info)
        return discovered

    def add_camera(self, camera_info):
        """Add a camera to the mock manager."""
        try:
            ip = camera_info['ip']

            # Create mock camera entry
            mock_camera = {
                'ip': ip,
                'name': camera_info.get('name', f'Mock Camera {ip}'),
                'location': camera_info.get('location', 'Mock Location'),
                'manufacturer': 'Mock Manufacturer',
                'model': 'Mock Camera',
                'status': 'connected',
                'stream_uri': camera_info.get('rtsp_url', f'rtsp://{ip}:554/stream')
            }

            self.cameras[ip] = {
                'camera': None,
                'info': mock_camera,
                'stream': None
            }

            logger.info(f"Added mock camera at {ip}")
            return True

        except Exception as e:
            logger.error(f"Error adding mock camera: {str(e)}")
            return False, str(e)

    def delete_camera(self, camera_id):
        """Delete a camera from the mock manager."""
        if camera_id in self.cameras:
            del self.cameras[camera_id]
            logger.info(f"Deleted mock camera {camera_id}")
            return True
        return False

    def get_stream_uri(self, ip):
        """Get the stream URI for a mock camera."""
        if ip in self.cameras:
            return self.cameras[ip]['info'].get('stream_uri')
        return None

    def get_camera_stream(self, ip):
        """Get the RTSP stream URL for a mock camera."""
        return self.get_stream_uri(ip)

    def try_connect_camera(self, ip, port=80):
        """Mock camera connection test."""
        # Always return a mock camera for testing
        return {
            'ip': ip,
            'port': port,
            'manufacturer': 'Mock Manufacturer',
            'model': 'Mock Camera',
            'type': 'Mock Camera',
            'requires_auth': False,
            'status': 'detected'
        }