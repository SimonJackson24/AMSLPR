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
import asyncio
from onvif_zeep import ONVIFCamera
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
        ]
        
        logger.info("ONVIF camera manager initialized")
    
    async def discover_cameras(self, timeout=2):
        """
        Discover ONVIF cameras on the network using WS-Discovery.
        
        Args:
            timeout (int): Timeout in seconds for discovery
            
        Returns:
            list: List of discovered camera information dictionaries
        """
        logger.info("Starting camera discovery...")
        discovered_cameras = []
        
        # Create UDP socket for discovery
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        
        # WS-Discovery message
        discovery_msg = """<?xml version="1.0" encoding="UTF-8"?>
        <e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery" xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
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
        
        try:
            # Send discovery message
            sock.sendto(discovery_msg.encode(), ('239.255.255.250', 3702))
            sock.settimeout(timeout)
            
            # Listen for responses
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(65535)
                    if data and addr:
                        ip = addr[0]
                        logger.info(f"Found potential camera at {ip}")
                        
                        # Try to connect with default credentials
                        for username, password in self.default_credentials:
                            try:
                                cam = ONVIFCamera(ip, 80, username, password, wsdl_dir=self.wsdl_dir)
                                
                                # Get device information
                                device_info = cam.devicemgmt.GetDeviceInformation()
                                media_service = cam.create_media_service()
                                profiles = media_service.GetProfiles()
                                
                                # Get stream URI
                                token = profiles[0].token
                                stream_setup = {
                                    'Stream': 'RTP-Unicast',
                                    'Transport': {
                                        'Protocol': 'RTSP'
                                    }
                                }
                                stream_uri = media_service.GetStreamUri(stream_setup, token)
                                
                                camera_info = {
                                    'ip': ip,
                                    'port': 80,
                                    'username': username,
                                    'password': password,
                                    'manufacturer': device_info.Manufacturer,
                                    'model': device_info.Model,
                                    'serial_number': device_info.SerialNumber,
                                    'stream_uri': stream_uri.Uri
                                }
                                
                                discovered_cameras.append(camera_info)
                                logger.info(f"Successfully connected to camera at {ip}")
                                break
                                
                            except Exception as e:
                                logger.debug(f"Failed to connect to {ip} with credentials {username}:{password}: {str(e)}")
                                continue
                
                except socket.timeout:
                    continue
                
        except Exception as e:
            logger.error(f"Error during camera discovery: {str(e)}")
        
        finally:
            sock.close()
        
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
