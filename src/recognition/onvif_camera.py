#!/usr/bin/env python3
"""
ONVIF Camera module for connecting to IP cameras using the ONVIF protocol.

This module provides functionality to discover, connect to, and stream from
ONVIF-compatible IP cameras for license plate recognition.
"""

import os
import time
import socket
import logging
from onvif.client import ONVIFCamera
from urllib.parse import urlparse
from src.utils.security import CredentialManager
import cv2
import numpy as np
from datetime import datetime
import zeep

logger = logging.getLogger('AMSLPR.recognition.onvif_camera')

def zeep_pythonvalue(self, xmlvalue):
    """Convert XML values to Python values."""
    return xmlvalue

# Patch zeep to handle ONVIF responses correctly
zeep.xsd.simple.AnySimpleType.pythonvalue = zeep_pythonvalue

class ONVIFCameraManager:
    """
    Class for managing ONVIF-compatible IP cameras.
    """
    def __init__(self, config=None):
        """
        Initialize the ONVIF camera manager.
        
        Args:
            config (dict): Configuration dictionary containing camera settings
        """
        self.config = config or {}
        self.cameras = {}
        self.credential_manager = CredentialManager()
        self.wsdl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wsdl')
        
        # Default credentials for camera discovery
        self.default_credentials = [
            ('admin', 'admin'),
            ('Admin', 'Admin'),
            ('admin', 'Admin123'),
            ('admin', '1234'),
            ('admin', 'password'),
            ('admin', ''),  # Some cameras use blank password
            ('root', 'root'),  # Added more common credentials
            ('root', 'pass'),
            ('root', 'admin')
        ]
        
        # Common ONVIF ports
        self.onvif_ports = [80, 8080, 8000, 8081, 8899]
        
        logger.info("ONVIF camera manager initialized")

    def get_all_cameras(self):
        """
        Get all registered cameras.
        
        Returns:
            dict: Dictionary of all registered cameras with their information
        """
        return self.cameras

    def try_connect_camera(self, ip, port=80):
        """
        Try to connect to a camera at a specific IP and port using default credentials.
        
        Args:
            ip (str): IP address of the camera
            port (int): Port number to try
            
        Returns:
            dict: Camera information if connection successful, None otherwise
        """
        logger.debug(f"Trying to connect to camera at {ip}:{port}")
        
        for username, password in self.default_credentials:
            try:
                camera = ONVIFCamera(ip, port, username, password, self.wsdl_dir, timeout=2)
                media_service = camera.create_media_service()
                profiles = media_service.GetProfiles()
                
                if profiles:
                    # Get device information
                    device_info = camera.devicemgmt.GetDeviceInformation()
                    
                    # Get stream URI for the first profile
                    token = profiles[0].token
                    stream_setup = {
                        'Stream': 'RTP-Unicast',
                        'Transport': {'Protocol': 'RTSP'}
                    }
                    stream_uri = media_service.GetStreamUri(stream_setup, token)
                    
                    camera_info = {
                        'ip': ip,
                        'port': port,
                        'username': username,
                        'password': password,
                        'profiles': [{'token': p.token, 'name': p.Name} for p in profiles],
                        'manufacturer': device_info.Manufacturer,
                        'model': device_info.Model,
                        'firmware': device_info.FirmwareVersion,
                        'serial': device_info.SerialNumber,
                        'stream_uri': stream_uri.Uri,
                        'status': 'discovered'
                    }
                    logger.info(f"Successfully connected to camera at {ip}:{port}")
                    return camera_info
            except Exception as e:
                logger.debug(f"Failed to connect to {ip}:{port} with credentials {username}: {str(e)}")
                continue
        return None

    def discover_cameras(self, timeout=2, known_ips=None):
        """
        Discover ONVIF cameras on the network using WS-Discovery and try known IPs.
        
        Args:
            timeout (int): Timeout in seconds for discovery
            known_ips (list): List of known IP addresses to try
            
        Returns:
            list: List of discovered camera information dictionaries
        """
        discovered_cameras = []
        known_ips = known_ips or []
        
        # First, try known IP addresses
        for ip in known_ips:
            logger.info(f"Trying known IP address: {ip}")
            for port in self.onvif_ports:
                camera_info = self.try_connect_camera(ip, port)
                if camera_info:
                    discovered_cameras.append(camera_info)
                    break
        
        try:
            # Create a UDP socket for discovery
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.settimeout(timeout)

            # WS-Discovery message
            message = """<?xml version="1.0" encoding="UTF-8"?>
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

            # Send discovery message
            sock.sendto(message.encode('utf-8'), ('239.255.255.250', 3702))

            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(65535)
                    if data:
                        ip = addr[0]
                        if ip not in [cam['ip'] for cam in discovered_cameras]:
                            logger.debug(f"Found potential camera at {ip}")
                            for port in self.onvif_ports:
                                camera_info = self.try_connect_camera(ip, port)
                                if camera_info:
                                    discovered_cameras.append(camera_info)
                                    break
                except socket.timeout:
                    break

            sock.close()

        except Exception as e:
            logger.error(f"Error during camera discovery: {str(e)}")

        logger.info(f"Discovery complete. Found {len(discovered_cameras)} cameras")
        return discovered_cameras

    def add_camera(self, camera_info):
        """
        Add a camera to the manager.
        
        Args:
            camera_info (dict): Camera information including connection details
            
        Returns:
            bool: True if camera was added successfully
        """
        try:
            ip = camera_info['ip']
            port = camera_info.get('port', 80)
            username = camera_info['username']
            password = camera_info['password']
            
            # Initialize camera connection
            cam = ONVIFCamera(ip, port, username, password, wsdl_dir=self.wsdl_dir)
            
            # Store camera info
            self.cameras[ip] = {
                'camera': cam,
                'info': camera_info
            }
            
            logger.info(f"Successfully added camera at {ip}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add camera: {str(e)}")
            return False
    
    def get_camera_stream(self, ip):
        """
        Get the RTSP stream URL for a camera.
        
        Args:
            ip (str): IP address of the camera
            
        Returns:
            str: RTSP stream URL
        """
        if ip not in self.cameras:
            logger.error(f"Camera {ip} not found")
            return None
            
        return self.cameras[ip]['info']['stream_uri']

def init_camera_manager(config):
    """
    Initialize the camera manager with the application configuration.
    
    Args:
        config (dict): Application configuration
        
    Returns:
        ONVIFCameraManager: Initialized camera manager instance
    """
    try:
        manager = ONVIFCameraManager(config)
        logger.info("Camera manager initialized successfully")
        return manager
    except Exception as e:
        logger.error(f"Failed to initialize camera manager: {str(e)}")
        return None
