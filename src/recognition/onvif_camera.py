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
import asyncio
import numpy as np
from datetime import datetime
from onvif import ONVIFCamera, ONVIFService
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
        self.credential_manager = CredentialManager()
        
        # Default configuration values
        self.discovery_enabled = config.get('discovery_enabled', True)
        self.discovery_interval = config.get('discovery_interval', 60)  # seconds
        self.default_username = config.get('default_username', 'admin')
        self.default_password = config.get('default_password', 'admin')
        
        # Create event loop for async operations
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize pre-configured cameras
        self.loop.run_until_complete(self._init_cameras())
    
    async def _init_cameras(self):
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
                    camera_config['encrypted_credentials'] = self.credential_manager.encrypt_credentials(credentials)
                    camera_config.pop('username', None)
                    camera_config.pop('password', None)
                
                await self.add_camera(
                    camera_id=camera_id,
                    ip=camera_config.get('ip'),
                    port=camera_config.get('port', 80),
                    name=camera_config.get('name', f"Camera {camera_id}"),
                    location=camera_config.get('location', 'Unknown')
                )
            except Exception as e:
                logger.error(f"Error initializing camera {camera_config.get('id')}: {e}")
    
    async def add_camera(self, camera_id, ip, port=80, name=None, location=None):
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
            await camera.update_xaddrs()  # Initialize services
            
            # Get camera information
            device_info = await camera.devicemgmt.GetDeviceInformation()
            
            # Get camera media service
            media_service = camera.create_media_service()
            
            # Get camera profiles
            profiles = await media_service.GetProfiles()
            
            # Get stream URI for the first profile
            token = profiles[0].token
            stream_setup = {
                'Stream': 'RTP-Unicast',
                'Transport': {
                    'Protocol': 'RTSP'
                }
            }
            stream_uri = await media_service.GetStreamUri(stream_setup, token)
            
            # Get imaging service for HLC/WDR configuration
            imaging_service = camera.create_imaging_service()
            video_source_token = profiles[0].VideoSourceConfiguration.SourceToken
            
            # Store camera information
            self.cameras[camera_id] = {
                'id': camera_id,
                'ip': ip,
                'port': port,
                'name': name or f"Camera {camera_id}",
                'location': location or 'Unknown',
                'manufacturer': device_info.Manufacturer,
                'model': device_info.Model,
                'serial': device_info.SerialNumber,
                'stream_uri': stream_uri.Uri,
                'profile_token': token,
                'video_source_token': video_source_token,
                'camera': camera,
                'media_service': media_service,
                'imaging_service': imaging_service
            }
            
            logger.info(f"Successfully added camera {camera_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding camera {camera_id}: {e}")
            return False
    
    async def configure_camera_imaging(self, camera_id, hlc_enabled=None, hlc_level=None, 
                                    wdr_enabled=None, wdr_level=None):
        """
        Configure camera imaging settings including HLC and WDR.
        
        Args:
            camera_id (str): Camera identifier
            hlc_enabled (bool): Enable/disable High Light Compensation
            hlc_level (float): HLC level (0.0 to 1.0)
            wdr_enabled (bool): Enable/disable Wide Dynamic Range
            wdr_level (float): WDR level (0.0 to 1.0)
        """
        try:
            camera_info = self.cameras.get(camera_id)
            if not camera_info:
                raise ValueError(f"Camera {camera_id} not found")
            
            imaging_service = camera_info['imaging_service']
            video_source_token = camera_info['video_source_token']
            
            # Get current settings
            settings = await imaging_service.GetImagingSettings({'VideoSourceToken': video_source_token})
            
            # Create settings type for modification
            new_settings = camera_info['camera'].imaging.create_type('ImagingSettings20')
            
            # Update HLC settings if provided
            if hlc_enabled is not None and hasattr(new_settings, 'HighlightCompensation'):
                new_settings.HighlightCompensation.Mode = 'ON' if hlc_enabled else 'OFF'
                if hlc_level is not None:
                    new_settings.HighlightCompensation.Level = max(0.0, min(1.0, hlc_level))
            
            # Update WDR settings if provided
            if wdr_enabled is not None and hasattr(new_settings, 'WideDynamicRange'):
                new_settings.WideDynamicRange.Mode = 'ON' if wdr_enabled else 'OFF'
                if wdr_level is not None:
                    new_settings.WideDynamicRange.Level = max(0.0, min(1.0, wdr_level))
            
            # Apply settings
            await imaging_service.SetImagingSettings({
                'VideoSourceToken': video_source_token,
                'ImagingSettings': new_settings
            })
            
            logger.info(f"Successfully updated imaging settings for camera {camera_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error configuring imaging for camera {camera_id}: {e}")
            return False
    
    def get_stream_url(self, camera_id):
        """Get the RTSP stream URL for a camera."""
        camera = self.cameras.get(camera_id)
        if camera:
            return camera.get('stream_uri')
        return None
    
    def get_camera_info(self, camera_id):
        """Get information about a specific camera."""
        return self.cameras.get(camera_id)
    
    def get_all_cameras(self):
        """Get information about all cameras."""
        return {k: {key: val for key, val in v.items() if not callable(val)} 
                for k, v in self.cameras.items()}
