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
import ipaddress
import concurrent.futures
import threading
import requests

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
        
        # Common ONVIF ports
        self.onvif_ports = [80, 8080, 8000, 8081, 8899, 554]  # Added RTSP port
        
        # Common RTSP paths
        self.rtsp_paths = [
            'h264Preview_01_main',
            'h264Preview_01_sub',
            'cam/realmonitor',
            'videoMain',
            'video1',
            'live/ch0',
            'live/ch00_0',
            'stream1',
            'live',
            'media/video1',
            'cam1/h264'
        ]
        
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
        Try to detect a camera at a specific IP and port without authentication.
        
        Args:
            ip (str): IP address of the camera
            port (int): Port number to try
            
        Returns:
            dict: Camera information if detected, None otherwise
        """
        logger.debug(f"Checking for camera at {ip}:{port}")
        
        # For RTSP port, just check if the port is open
        if port == 554:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((ip, port))
                sock.close()
                
                if result == 0:
                    logger.info(f"Found potential RTSP camera at {ip}:{port}")
                    return {
                        'ip': ip,
                        'port': port,
                        'type': 'RTSP Camera',
                        'requires_auth': True,
                        'status': 'detected'
                    }
            except Exception as e:
                logger.debug(f"Error checking RTSP port at {ip}:{port}: {str(e)}")
                return None
        
        # For other ports, try ONVIF device discovery without auth
        try:
            # Try to connect to device service endpoint
            url = f"http://{ip}:{port}/onvif/device_service"
            response = requests.get(url, timeout=1)
            
            if response.status_code in [401, 403]:  # Authentication required
                logger.info(f"Found potential ONVIF camera at {ip}:{port}")
                return {
                    'ip': ip,
                    'port': port,
                    'type': 'ONVIF Camera',
                    'requires_auth': True,
                    'status': 'detected'
                }
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error checking ONVIF endpoint at {ip}:{port}: {str(e)}")
            return None
        
        return None

    def get_local_network(self):
        """Get the local network address range."""
        try:
            # Create a temporary socket to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Get network address range (assuming /24 subnet)
            network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
            return network
        except Exception as e:
            logger.error(f"Error getting local network: {str(e)}")
            return None

    def scan_network(self, timeout=2):
        """
        Scan the local network for potential cameras.
        
        Args:
            timeout (int): Timeout in seconds for each connection attempt
            
        Returns:
            list: List of discovered camera information dictionaries
        """
        discovered_cameras = []
        network = self.get_local_network()
        
        if not network:
            return []
        
        # Use a thread pool to scan IPs in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for ip in network.hosts():
                ip_str = str(ip)
                # Skip broadcast and network addresses
                if ip_str.endswith('.0') or ip_str.endswith('.255'):
                    continue
                    
                # First check RTSP port
                futures.append(executor.submit(self.try_connect_camera, ip_str, 554))
                
                # Then check common ONVIF ports
                for port in [80, 8080, 8000, 8081, 8899]:
                    futures.append(executor.submit(self.try_connect_camera, ip_str, port))
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        # Only add if we haven't found this IP yet
                        if not any(cam['ip'] == result['ip'] for cam in discovered_cameras):
                            discovered_cameras.append(result)
                except Exception as e:
                    logger.debug(f"Error in scan task: {str(e)}")
        
        return discovered_cameras

    def discover_cameras(self, timeout=2):
        """
        Discover cameras on the network using both WS-Discovery and network scanning.
        
        Args:
            timeout (int): Timeout in seconds for discovery
            
        Returns:
            list: List of discovered camera information dictionaries
        """
        discovered_cameras = []
        
        try:
            # First, try WS-Discovery
            logger.info("Starting WS-Discovery...")
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                sock.settimeout(timeout)

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

                sock.sendto(message.encode('utf-8'), ('239.255.255.250', 3702))

                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        data, addr = sock.recvfrom(65535)
                        if data:
                            ip = addr[0]
                            if not any(cam['ip'] == ip for cam in discovered_cameras):
                                logger.info(f"Found camera via WS-Discovery at {ip}")
                                discovered_cameras.append({
                                    'ip': ip,
                                    'type': 'ONVIF Camera',
                                    'requires_auth': True,
                                    'status': 'detected'
                                })
                    except socket.timeout:
                        break

                sock.close()

            except Exception as e:
                logger.error(f"Error during WS-Discovery: {str(e)}")

            # Then, perform network scan
            logger.info("Starting network scan...")
            scan_results = self.scan_network(timeout)
            
            # Merge results, avoiding duplicates
            for camera in scan_results:
                if not any(cam['ip'] == camera['ip'] for cam in discovered_cameras):
                    discovered_cameras.append(camera)

            logger.info(f"Discovery complete. Found {len(discovered_cameras)} cameras")
            return discovered_cameras

        except Exception as e:
            logger.error(f"Error during camera discovery: {str(e)}")
            return []

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
