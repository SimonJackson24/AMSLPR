# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

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
from onvif2_zeep import ONVIFCamera, ONVIFService, ONVIFError
from urllib.parse import urlparse
from src.utils.security import CredentialManager
import socket
import struct
import threading
from queue import Queue
import zeep

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
        self.default_password = config.get('default_password', 'Aut0mate2048')
        
        # Fix for zeep's type handling
        zeep.xsd.simple.AnySimpleType.pythonvalue = lambda self, xmlvalue: xmlvalue
        
        # Initialize cameras without using event loop
        self._init_cameras_sync()
    
    def _init_cameras_sync(self):
        """
        Initialize pre-configured cameras synchronously.
        """
        preconfigured_cameras = self.config.get('cameras', [])
        for camera_config in preconfigured_cameras:
            try:
                camera_id = camera_config.get('id')
                if not camera_id:
                    continue
                    
                # Store camera config for later connection
                self.cameras[camera_id] = {
                    'id': camera_id,
                    'ip': camera_config.get('ip'),
                    'port': camera_config.get('port', 80),
                    'name': camera_config.get('name', f"Camera {camera_id}"),
                    'location': camera_config.get('location', 'Unknown'),
                    'username': camera_config.get('username', self.default_username),
                    'password': camera_config.get('password', self.default_password),
                    'connected': False,
                    'last_error': None,
                    'capabilities': {}
                }
                
                logger.info(f"Added pre-configured camera {camera_id} from config")
            except Exception as e:
                logger.error(f"Error initializing camera from config: {e}")
    
    async def _init_cameras(self):
        """
        Initialize pre-configured cameras from config.
        This is a placeholder for async initialization if needed.
        """
        pass
    
    async def add_camera(self, camera_id, ip, port=80, name=None, location=None, username=None, password=None, rtsp_url=None):
        """
        Add a new ONVIF camera to the manager.
        
        Args:
            camera_id (str): Unique identifier for the camera
            ip (str): IP address of the camera
            port (int): Port number for the camera (default: 80)
            name (str): Human-readable name for the camera
            location (str): Physical location of the camera
            username (str): Username for camera authentication
            password (str): Password for camera authentication
            rtsp_url (str): Optional direct RTSP stream URL
            
        Returns:
            bool: True if camera was added successfully, False otherwise
        """
        try:
            if camera_id in self.cameras:
                logger.warning(f"Camera with ID {camera_id} already exists")
                return False
            
            # Use provided credentials or fall back to defaults
            cam_username = username or self.default_username
            cam_password = password or self.default_password
            
            # Store basic camera information first
            self.cameras[camera_id] = {
                'id': camera_id,
                'ip': ip,
                'port': port,
                'name': name or f"Camera {camera_id}",
                'location': location or 'Unknown',
                'username': cam_username,
                'password': cam_password,
                'connected': False,
                'last_error': None,
                'capabilities': {},
                'rtsp_url': rtsp_url  # Store RTSP URL if provided
            }

            # If RTSP URL is provided, skip ONVIF discovery
            if rtsp_url:
                logger.info(f"Using direct RTSP URL for camera {camera_id}: {rtsp_url}")
                self.cameras[camera_id].update({
                    'connected': True,
                    'stream_uri': rtsp_url,
                    'using_rtsp': True
                })
                return True

            # Otherwise proceed with ONVIF discovery
            camera = ONVIFCamera(ip, port, cam_username, cam_password)
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
            
            # Update camera information
            self.cameras[camera_id].update({
                'connected': True,
                'manufacturer': device_info.Manufacturer,
                'model': device_info.Model,
                'serial_number': device_info.SerialNumber,
                'firmware_version': device_info.FirmwareVersion,
                'stream_uri': stream_uri.Uri,
                'using_rtsp': False,
                'device': camera,
                'media_service': media_service,
                'imaging_service': imaging_service,
                'video_source_token': video_source_token,
                'profile_token': token
            })
            
            logger.info(f"Successfully added camera {camera_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding camera {camera_id}: {e}")
            if camera_id in self.cameras:
                self.cameras[camera_id]['last_error'] = str(e)
            return False
    
    def discover_cameras(self, timeout=5):
        """
        Discover ONVIF cameras on the network using WS-Discovery.
        
        Args:
            timeout (int): Discovery timeout in seconds
            
        Returns:
            list: List of discovered cameras with their info
        """
        discovered = []
        logger.debug("Starting camera discovery...")
        
        try:
            # Create UDP socket for discovery
            logger.debug("Creating UDP socket for discovery...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            try:
                # Set socket options
                logger.debug("Setting socket options...")
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                # Bind to all interfaces
                sock.bind(('', 0))
                logger.debug("Successfully bound to all interfaces")
                
                sock.settimeout(timeout)
                
                # WS-Discovery probe message
                probe = """<?xml version="1.0" encoding="UTF-8"?>
                <e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
                           xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
                           xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
                           xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
                    <e:Header>
                        <w:MessageID>uuid:84ede3de-7dec-11d0-c360-f01234567890</w:MessageID>
                        <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
                        <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
                    </e:Header>
                    <e:Body>
                        <d:Probe>
                            <d:Types>dn:NetworkVideoTransmitter</d:Types>
                        </d:Probe>
                    </e:Body>
                </e:Envelope>"""
                
                # Send discovery probe
                logger.debug("Sending discovery probe...")
                try:
                    sock.sendto(probe.encode(), ('239.255.255.250', 3702))
                    logger.debug("Discovery probe sent successfully")
                except Exception as e:
                    logger.error(f"Failed to send discovery probe: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    raise
                
                # Collect responses
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        data, addr = sock.recvfrom(65535)
                        if data:
                            logger.debug(f"Received response from {addr}")
                            try:
                                # Try different common credentials
                                credentials = [
                                    (self.default_username, self.default_password),
                                    ('admin', 'admin'),
                                    ('admin', ''),
                                    ('Admin', 'Admin'),
                                    ('root', 'root')
                                ]
                                
                                device_info = None
                                for username, password in credentials:
                                    try:
                                        # Get WSDL directory from package location
                                        import onvif2_zeep
                                        wsdl_dir = os.path.join(os.path.dirname(onvif2_zeep.__file__), 'wsdl')
                                        logger.debug(f"Using WSDL directory: {wsdl_dir}")
                                        
                                        cam = ONVIFCamera(addr[0], 80, username, password, wsdl_dir=wsdl_dir)
                                        device_info = cam.devicemgmt.GetDeviceInformation()
                                        logger.debug(f"Successfully connected to {addr[0]} with {username}:{password}")
                                        break
                                    except Exception as e:
                                        logger.debug(f"Failed to connect with {username}:{password}: {str(e)}")
                                        continue
                                
                                if device_info:
                                    camera_info = {
                                        'ip': addr[0],
                                        'port': 80,
                                        'manufacturer': device_info.get('Manufacturer', 'Unknown'),
                                        'model': device_info.get('Model', 'Unknown'),
                                        'firmware_version': device_info.get('FirmwareVersion', ''),
                                        'serial_number': device_info.get('SerialNumber', '')
                                    }
                                else:
                                    # Basic info without device details
                                    camera_info = {
                                        'ip': addr[0],
                                        'port': 80,
                                        'manufacturer': 'Unknown',
                                        'model': 'Unknown'
                                    }
                                
                                # Check if this camera is already in the list
                                if not any(d['ip'] == addr[0] for d in discovered):
                                    discovered.append(camera_info)
                                    logger.debug(f"Added camera: {camera_info}")
                                
                            except Exception as e:
                                logger.warning(f"Could not get device info from {addr[0]}: {str(e)}")
                                # Still add the camera with basic info
                                if not any(d['ip'] == addr[0] for d in discovered):
                                    discovered.append({
                                        'ip': addr[0],
                                        'port': 80,
                                        'manufacturer': 'Unknown',
                                        'model': 'Unknown'
                                    })
                    except socket.timeout:
                        logger.debug("Socket timeout, discovery complete")
                        break
                    except Exception as e:
                        logger.error(f"Error receiving discovery response: {str(e)}")
                        continue
            
            finally:
                sock.close()
                logger.debug("Discovery socket closed")
        
        except Exception as e:
            logger.error(f"Error in discover_cameras: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
        logger.info(f"Discovery completed. Found {len(discovered)} devices")
        return discovered
    
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
