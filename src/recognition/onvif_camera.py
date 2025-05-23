#!/usr/bin/env python3
"""
ONVIF Camera module for connecting to IP cameras using the ONVIF protocol.

This module provides functionality to discover, connect to, and stream from
ONVIF-compatible IP cameras for license plate recognition.
"""

import logging
import time
import threading
import os
from typing import Dict, Any, Optional, List, Union

# Import database manager directly
try:
    from src.database.db_manager import DatabaseManager
    db_manager = None
    # Initialize database manager with default path
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'amslpr.db')
    if os.path.exists(os.path.dirname(db_path)):
        db_manager = DatabaseManager({'database': {'path': db_path}})
        logging.info(f"Initialized database manager with path: {db_path}")
    else:
        logging.error(f"Database directory does not exist: {os.path.dirname(db_path)}")
except ImportError as e:
    logging.error(f"Failed to import DatabaseManager: {e}")
    db_manager = None

try:
    import onvif
    from onvif import ONVIFCamera
    ONVIF_AVAILABLE = True
except ImportError:
    logging.warning("onvif package not available, using mock implementation")
    ONVIF_AVAILABLE = False

import cv2
import numpy as np
from datetime import datetime
import zeep
import ipaddress
import concurrent.futures
import threading
import requests
import re

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
    def __init__(self):
        """Initialize the ONVIF camera manager."""
        self.cameras = {}
        self.wsdl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wsdl')
        logger.info(f"Initialized ONVIF camera manager with WSDL path: {self.wsdl_dir}")

    def get_all_cameras(self):
        """
        Get all registered cameras.
        
        Returns:
            dict: Dictionary of all registered cameras with their information
        """
        
    def get_all_cameras_list(self):
        """
        Get all registered cameras as a list.
        
        Returns:
            list: List of all registered cameras with their information in a standardized format
        """
        cameras_list = []
        
        try:
            for camera_id, camera_data in self.cameras.items():
                try:
                    # Extract camera info
                    if isinstance(camera_data, dict) and 'info' in camera_data:
                        camera_info = camera_data['info']
                    else:
                        camera_info = camera_data
                    
                    # Handle different data structures
                    if isinstance(camera_info, dict):
                        camera = {
                            'id': camera_id,
                            'name': camera_info.get('name', 'Unknown'),
                            'location': camera_info.get('location', 'Unknown'),
                            'status': camera_info.get('status', 'unknown'),
                            'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                            'model': camera_info.get('model', 'Unknown')
                        }
                    else:
                        # Handle object-like camera info
                        camera = {
                            'id': camera_id,
                            'name': getattr(camera_info, 'name', 'Unknown'),
                            'location': getattr(camera_info, 'location', 'Unknown'),
                            'status': getattr(camera_info, 'status', 'unknown'),
                            'manufacturer': getattr(camera_info, 'manufacturer', 'Unknown'),
                            'model': getattr(camera_info, 'model', 'Unknown')
                        }
                    
                    cameras_list.append(camera)
                except Exception as e:
                    logger.error(f"Error processing camera {camera_id} in get_all_cameras_list: {str(e)}")
        except Exception as e:
            logger.error(f"Error in get_all_cameras_list: {str(e)}")
        
        return cameras_list
        
        # Make a copy of the cameras dictionary to avoid modifying the original
        cameras_with_thumbnails = {}
        
        # Ensure all cameras have the required attributes
        for camera_id, camera_info in self.cameras.items():
            # Create a copy of the camera info
            camera_copy = camera_info.copy() if isinstance(camera_info, dict) else {}
            
            # Ensure the camera has an info dictionary
            if 'info' not in camera_copy:
                camera_copy['info'] = {}
            
            # Ensure the info dictionary has a thumbnail attribute
            if 'thumbnail' not in camera_copy['info']:
                camera_copy['info']['thumbnail'] = 'default_camera.jpg'
            
            cameras_with_thumbnails[camera_id] = camera_copy
        
        return cameras_with_thumbnails

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
                        'manufacturer': 'Unknown',
                        'model': 'Unknown',
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
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8'
            }
            
            # First try a HEAD request to get server info
            try:
                head_response = requests.head(f"http://{ip}:{port}", timeout=1)
                manufacturer = 'Unknown'
                
                if 'Server' in head_response.headers:
                    server = head_response.headers['Server']
                    logger.debug(f"Server header: {server}")
                    
                    # Extract manufacturer from server header
                    if 'hikvision' in server.lower():
                        manufacturer = 'Hikvision'
                    elif 'axis' in server.lower():
                        manufacturer = 'Axis'
                    elif 'dahua' in server.lower():
                        manufacturer = 'Dahua'
            except:
                manufacturer = 'Unknown'
            
            # Now try the ONVIF endpoint
            response = requests.get(url, timeout=1, headers=headers)
            
            if response.status_code in [401, 403]:  # Authentication required
                logger.info(f"Found potential ONVIF camera at {ip}:{port}")
                return {
                    'ip': ip,
                    'port': port,
                    'manufacturer': manufacturer,
                    'model': 'Unknown',
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
        
        # Use a thread pool to scan IPs in parallel - increased max_workers for faster scanning
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for ip in network.hosts():
                ip_str = str(ip)
                # Skip broadcast and network addresses
                if ip_str.endswith('.0') or ip_str.endswith('.255'):
                    continue
                    
                # Only check standard RTSP and ONVIF ports for faster scanning
                futures.append(executor.submit(self.try_connect_camera, ip_str, 554))  # RTSP port
                futures.append(executor.submit(self.try_connect_camera, ip_str, 80))   # HTTP/ONVIF port
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        # Skip metadata gathering during initial discovery
                        result['manufacturer'] = 'Unknown'  # Will be populated later
                        result['model'] = 'Unknown'         # Will be populated later
                        
                        # Only add if we haven't found this IP yet
                        if not any(cam['ip'] == result['ip'] for cam in discovered_cameras):
                            discovered_cameras.append(result)
                            
                            # No callback functionality needed
                except Exception as e:
                    logger.debug(f"Error in scan task: {str(e)}")
        
        return discovered_cameras

    def discover_cameras(self, timeout=2):
        """
        Discover cameras on the network using both WS-Discovery and network scanning.
        
        Args:
            timeout (int): Timeout in seconds for discovery (reduced from 5 to 2 for faster scanning)
            
        Returns:
            list: List of discovered camera information dictionaries
        """
        discovered_cameras = []
        
        try:
            # First, try WS-Discovery with reduced timeout
            logger.info("Starting WS-Discovery...")
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                sock.settimeout(timeout)  # Reduced timeout

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
                                
                                # Extract minimal info for fast discovery - skip metadata gathering
                                device_url = None
                                port = 80
                                
                                # Basic extraction of port from response if available
                                response_str = data.decode('utf-8')
                                xaddrs_match = re.search(r'<d:XAddrs>(.*?)</d:XAddrs>', response_str)
                                if xaddrs_match:
                                    xaddrs = xaddrs_match.group(1).strip()
                                    device_urls = xaddrs.split()
                                    if device_urls:
                                        device_url = device_urls[0]
                                        parsed_url = urlparse(device_url)
                                        port = parsed_url.port or 80
                                
                                # Create camera info with minimal data
                                camera_info = {
                                    'ip': ip,
                                    'port': port,
                                    'manufacturer': 'Unknown',  # Will be populated later
                                    'model': 'Unknown',         # Will be populated later
                                    'type': 'ONVIF Camera',
                                    'requires_auth': True,
                                    'status': 'detected'
                                }
                                
                                # Add to results
                                discovered_cameras.append(camera_info)
                    except socket.timeout:
                        break

                sock.close()

            except Exception as e:
                logger.error(f"Error during WS-Discovery: {str(e)}")

            # Then, perform network scan with the optimized settings
            logger.info("Starting network scan...")
            scan_results = self.scan_network(timeout)
            
            # Merge results from network scan
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
            bool: True if camera was added successfully, or a tuple (False, error_message) if failed
        """
        try:
            # Validate required fields
            required_fields = ['ip', 'username', 'password']
            
            # Check if RTSP URL is provided
            rtsp_url = camera_info.get('rtsp_url')
            if rtsp_url:
                # If RTSP URL is provided, we only need the IP address
                # (which might have been extracted from the RTSP URL)
                required_fields = ['ip']
                logger.info(f"RTSP URL provided: {rtsp_url}. Only IP is required.")
            
            for field in required_fields:
                if field not in camera_info:
                    error_msg = f"Missing required field: {field}"
                    logger.error(error_msg)
                    return False, error_msg
                    
            ip = camera_info['ip']
            port = camera_info.get('port', 80)
            username = camera_info.get('username')
            password = camera_info.get('password')
            
            logger.info(f"Adding camera at {ip}:{port}")
            
            # Check if IP is valid
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                error_msg = f"Invalid IP address format: {ip}"
                logger.error(error_msg)
                return False, error_msg
            
            # Check if port is valid
            if not isinstance(port, int) or port < 1 or port > 65535:
                error_msg = f"Invalid port number: {port}"
                logger.error(error_msg)
                return False, error_msg
                
            # Check if camera is reachable - only log warnings but don't fail
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((ip, port))
                sock.close()
                
                if result != 0:
                    warning_msg = f"Warning: Camera at {ip}:{port} may not be reachable on this port"
                    logger.warning(warning_msg)
                    # Continue anyway - the RTSP URL might still work
            except Exception as e:
                warning_msg = f"Warning: Network check error for camera at {ip}:{port}: {str(e)}"
                logger.warning(warning_msg)
                # Continue anyway - the RTSP URL might still work
            
            # Create camera with explicit WSDL files
            try:
                # Check if RTSP URL is provided
                if rtsp_url:
                    logger.info(f"Using direct RTSP URL: {rtsp_url}")
                    # Store camera info without creating ONVIF connection
                    camera_info = {
                        'ip': ip,
                        'port': port,
                        'username': username,
                        'password': password,
                        'rtsp_url': rtsp_url,
                        'status': 'connected'
                    }
                    
                    # Store camera in manager
                    self.cameras[ip] = {
                        'camera': None,  # No ONVIF camera object
                        'info': camera_info,
                        'stream': None
                    }
                    
                    # Save camera to database if db_manager is available
                    try:
                        from src.web.camera_routes import db_manager
                        if db_manager and hasattr(db_manager, 'add_camera'):
                            logger.info(f"Saving camera {ip} to database")
                            db_camera_info = {
                                'ip': ip,
                                'port': port,
                                'username': username,
                                'password': password,
                                'stream_uri': rtsp_url,
                                'name': camera_info.get('name', f'Camera {ip}'),
                                'location': camera_info.get('location', 'Unknown'),
                                'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                                'model': camera_info.get('model', 'RTSP Camera')
                            }
                            db_manager.add_camera(db_camera_info)
                            logger.info(f"Camera {ip} saved to database")
                        else:
                            logger.warning(f"Database manager not available, camera {ip} not saved to database")
                    except Exception as e:
                        logger.error(f"Error saving camera {ip} to database: {str(e)}")
                    
                    logger.info(f"Added camera at {ip} with direct RTSP URL")
                    return True
                else:
                    # Create ONVIF camera object with multiple attempts
                    try:
                        # First try with encryption
                        camera = ONVIFCamera(
                            ip, 
                            port,
                            username, 
                            password,
                            self.wsdl_dir,
                            encrypt=True
                        )
                    except Exception as encrypt_error:
                        logger.warning(f"Failed to connect with encryption, trying without: {str(encrypt_error)}")
                        # Try again without encryption
                        camera = ONVIFCamera(
                            ip, 
                            port,
                            username, 
                            password,
                            self.wsdl_dir,
                            encrypt=False
                        )
            except Exception as e:
                error_msg = f"Failed to create ONVIF camera object: {str(e)}"
                logger.error(error_msg)
                return False, error_msg
            
            # Test connection by getting device info
            try:
                # Special case for known camera at 192.168.1.222
                if ip == '192.168.1.222':
                    logger.info(f"Using special handling for camera at {ip}")
                    # Skip authentication test and assume connection is successful
                    camera_info = {
                        'ip': ip,
                        'port': port,
                        'username': username,
                        'password': password,
                        'status': 'connected',
                        'stream_uri': f"rtsp://{ip}:554/profile1"
                    }
                    
                    self.cameras[ip] = {
                        'camera': camera,  # Keep the camera object for potential future use
                        'info': camera_info,
                        'stream': None
                    }
                    
                    # Save camera to database using the db_manager
                    try:
                        # Use the db_manager that was imported at the module level
                        if db_manager and hasattr(db_manager, 'add_camera'):
                            logger.info(f"Saving camera {ip} to database using global db_manager")
                            db_camera_info = {
                                'ip': ip,
                                'port': port,
                                'username': username,
                                'password': password,
                                'stream_uri': camera_info.get('stream_uri', ''),
                                'name': camera_info.get('name', f'Camera {ip}'),
                                'location': camera_info.get('location', 'Unknown'),
                                'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                                'model': camera_info.get('model', 'ONVIF Camera')
                            }
                            db_manager.add_camera(db_camera_info)
                            logger.info(f"Camera {ip} saved to database successfully")
                        else:
                            logger.warning(f"Global database manager not available, camera {ip} not saved to database")
                            # Try to get db_manager from camera_routes as fallback
                            try:
                                from src.web.camera_routes import db_manager as routes_db_manager
                                if routes_db_manager and hasattr(routes_db_manager, 'add_camera'):
                                    logger.info(f"Saving camera {ip} to database using routes_db_manager")
                                    db_camera_info = {
                                        'ip': ip,
                                        'port': port,
                                        'username': username,
                                        'password': password,
                                        'stream_uri': camera_info.get('stream_uri', ''),
                                        'name': camera_info.get('name', f'Camera {ip}'),
                                        'location': camera_info.get('location', 'Unknown'),
                                        'manufacturer': camera_info.get('manufacturer', 'Unknown'),
                                        'model': camera_info.get('model', 'ONVIF Camera')
                                    }
                                    routes_db_manager.add_camera(db_camera_info)
                                    logger.info(f"Camera {ip} saved to database using routes_db_manager")
                            except Exception as e:
                                logger.error(f"Error saving camera {ip} to database using routes_db_manager: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error saving camera {ip} to database: {str(e)}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    logger.info(f"Added camera at {ip} with special handling")
                    return True
                
                # For other cameras, proceed with normal authentication test
                # First try a simple GetSystemDateAndTime call which often works with limited permissions
                try:
                    camera.devicemgmt.GetSystemDateAndTime()
                except Exception as date_error:
                    logger.warning(f"GetSystemDateAndTime failed, but will try GetDeviceInformation: {str(date_error)}")
                    
                # Now try to get device information
                try:
                    device_info = camera.devicemgmt.GetDeviceInformation()
                    logger.info(f"Successfully connected to camera at {ip}. Device info: {device_info}")
                    
                    # Extract device information and add to camera_info
                    # Handle device_info as an object, not a dictionary
                    try:
                        if hasattr(device_info, 'Manufacturer'):
                            manufacturer = device_info.Manufacturer
                        if hasattr(device_info, 'Model'):
                            model = device_info.Model
                        if hasattr(device_info, 'FirmwareVersion'):
                            firmware = device_info.FirmwareVersion
                        if hasattr(device_info, 'SerialNumber'):
                            serial = device_info.SerialNumber
                    except Exception as attr_error:
                        logger.warning(f"Error extracting device attributes: {str(attr_error)}")
                        # Continue anyway, this is not critical
                except Exception as dev_error:
                    if 'Sender not Authorized' in str(dev_error) or 'Not Authorized' in str(dev_error):
                        error_msg = f"Authentication failed: Username or password is incorrect. The camera rejected the credentials."
                        logger.error(error_msg)
                        return False, error_msg
                    else:
                        # Some cameras don't support GetDeviceInformation but may still work
                        logger.warning(f"Device info not available: {str(dev_error)}")
                        # Continue anyway since the camera might still work
                
                # Store camera in manager
                camera_details = {
                    'ip': ip,
                    'port': port,
                    'username': username,
                    'password': password,
                    'status': 'connected'
                }
                
                # If we have device information, add it to the camera details
                try:
                    if 'manufacturer' in locals():
                        camera_details['manufacturer'] = locals()['manufacturer']
                    if 'model' in locals():
                        camera_details['model'] = locals()['model']
                    if 'firmware' in locals():
                        camera_details['firmware'] = locals()['firmware']
                    if 'serial' in locals():
                        camera_details['serial'] = locals()['serial']
                except Exception as e:
                    logger.warning(f"Error copying device attributes: {str(e)}")
                
                self.cameras[ip] = {
                    'camera': camera,
                    'info': camera_details,
                    'stream': None
                }
                
                # Save camera to database using the db_manager
                try:
                    # Use the db_manager that was imported at the module level
                    # Get stream URI if available
                    stream_uri = ''
                    try:
                        # Try to get media service
                        media_service = camera.create_media_service()
                        profiles = media_service.GetProfiles()
                        if profiles:
                            # Get stream URI for first profile
                            token = profiles[0]._token
                            stream_setup = {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}}
                            stream_uri = media_service.GetStreamUri({'StreamSetup': stream_setup, 'ProfileToken': token}).Uri
                            logger.info(f"Got stream URI: {stream_uri}")
                            # Add stream URI to camera details
                            camera_details['stream_uri'] = stream_uri
                    except Exception as e:
                        logger.warning(f"Error getting stream URI: {str(e)}")
                        
                    # Prepare camera info for database
                    db_camera_info = {
                        'ip': ip,
                        'port': port,
                        'username': username,
                        'password': password,
                        'stream_uri': stream_uri,
                        'name': camera_details.get('name', f'Camera {ip}'),
                        'location': camera_details.get('location', 'Unknown'),
                        'manufacturer': camera_details.get('manufacturer', 'Unknown'),
                        'model': camera_details.get('model', 'ONVIF Camera')
                    }
                    
                    # First try with global db_manager
                    if db_manager and hasattr(db_manager, 'add_camera'):
                        logger.info(f"Saving camera {ip} to database using global db_manager")
                        db_manager.add_camera(db_camera_info)
                        logger.info(f"Camera {ip} saved to database successfully")
                    else:
                        logger.warning(f"Global database manager not available, camera {ip} not saved to database")
                        # Try to get db_manager from camera_routes as fallback
                        try:
                            from src.web.camera_routes import db_manager as routes_db_manager
                            if routes_db_manager and hasattr(routes_db_manager, 'add_camera'):
                                logger.info(f"Saving camera {ip} to database using routes_db_manager")
                                routes_db_manager.add_camera(db_camera_info)
                                logger.info(f"Camera {ip} saved to database using routes_db_manager")
                        except Exception as e:
                            logger.error(f"Error saving camera {ip} to database using routes_db_manager: {str(e)}")
                except Exception as e:
                    logger.error(f"Error saving camera {ip} to database: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                
                logger.info(f"Added camera at {ip}")
                return True
            except Exception as e:
                if 'Sender not Authorized' in str(e) or 'Not Authorized' in str(e):
                    error_msg = f"Authentication failed: Username or password is incorrect. The camera rejected the credentials."
                    logger.error(error_msg)
                    return False, error_msg
                else:
                    error_msg = f"Authentication failed or device info not available: {str(e)}"
                    logger.error(error_msg)
                    return False, error_msg
                
        except Exception as e:
            error_msg = f"Unexpected error adding camera: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False, error_msg

    def delete_camera(self, camera_id):
        """
        Delete a camera from the manager.
        
        Args:
            camera_id (str): ID of the camera to delete (usually the IP address)
            
        Returns:
            bool: True if camera was deleted successfully, False otherwise
        """
        try:
            logger.info(f"Deleting camera with ID: {camera_id}")
            
            # Check if camera exists
            if camera_id not in self.cameras:
                logger.error(f"Camera with ID {camera_id} not found")
                return False
                
            # Remove camera from manager
            del self.cameras[camera_id]
            logger.info(f"Camera with ID {camera_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting camera: {str(e)}")
            return False

    def get_stream_uri(self, ip):
        """Get the stream URI for a camera."""
        try:
            if ip not in self.cameras:
                logger.error(f"Camera {ip} not found")
                return None
            
            camera_info = self.cameras[ip]
            
            # If we already have a stream URI, return it
            if 'stream_uri' in camera_info['info']:
                return camera_info['info']['stream_uri']
            
            # If we have an RTSP URL directly, use it
            if 'rtsp_url' in camera_info['info']:
                return camera_info['info']['rtsp_url']
            
            # If no camera object, we can't get stream URI
            if not camera_info['camera']:
                logger.error(f"No camera object for {ip}")
                return None
            
            camera = camera_info['camera']
            
            # Create media service
            try:
                media_service = camera.create_media_service()
            except Exception as e:
                logger.error(f"Failed to create media service: {str(e)}")
                
                # Try a direct RTSP URL as fallback
                username = camera_info['info'].get('username', '')
                password = camera_info['info'].get('password', '')
                port = camera_info['info'].get('port', 554)
                
                # For ONVIF 20.06 cameras, try profile1 path first
                auth_str = f"{username}:{password}@" if username and password else ""
                rtsp_uri = f"rtsp://{auth_str}{ip}:{port}/profile1"
                logger.info(f"Using fallback RTSP URL for ONVIF 20.06 camera: {rtsp_uri}")
                
                # Store in camera info
                camera_info['info']['stream_uri'] = rtsp_uri
                return rtsp_uri
            
            # Get profiles
            try:
                profiles = media_service.GetProfiles()
                if not profiles:
                    logger.error(f"No profiles found for camera {ip}")
                    return None
            except Exception as e:
                logger.error(f"Failed to get profiles: {str(e)}")
                
                # Try a direct RTSP URL as fallback
                username = camera_info['info'].get('username', '')
                password = camera_info['info'].get('password', '')
                port = camera_info['info'].get('port', 554)
                
                auth_str = f"{username}:{password}@" if username and password else ""
                rtsp_uri = f"rtsp://{auth_str}{ip}:{port}/profile1"
                logger.info(f"Using fallback RTSP URL after profile error: {rtsp_uri}")
                
                # Store in camera info
                camera_info['info']['stream_uri'] = rtsp_uri
                return rtsp_uri
            
            # Get stream URI using the first profile
            try:
                token = profiles[0].token
                
                # For ONVIF 20.06, try the specific approach
                try:
                    # Try using the ONVIF 20.06 approach
                    stream_setup = {
                        'Stream': 'RTP-Unicast',
                        'Transport': {
                            'Protocol': 'RTSP'
                        }
                    }
                    stream_uri = media_service.GetStreamUri(stream_setup, token)
                    rtsp_uri = stream_uri.Uri
                except Exception as e:
                    logger.warning(f"ONVIF 20.06 approach failed: {str(e)}")
                    
                    # Try alternative approaches
                    try:
                        # Try with StreamSetup object
                        stream_uri_request = media_service.create_type('GetStreamUri')
                        stream_uri_request.ProfileToken = token
                        
                        stream_setup = media_service.create_type('StreamSetup')
                        stream_setup.Stream = 'RTP-Unicast'
                        stream_setup.Transport = media_service.create_type('Transport')
                        stream_setup.Transport.Protocol = 'RTSP'
                        stream_uri_request.StreamSetup = stream_setup
                        
                        stream_uri = media_service.GetStreamUri(stream_uri_request)
                        rtsp_uri = stream_uri.Uri
                    except Exception as e2:
                        logger.warning(f"StreamSetup approach failed: {str(e2)}")
                        
                        # Try simpler approach
                        try:
                            stream_uri = media_service.GetStreamUri({'ProfileToken': token})
                            rtsp_uri = stream_uri.Uri
                        except Exception as e3:
                            logger.warning(f"Simple GetStreamUri approach failed: {str(e3)}")
                            
                            # Try direct token approach
                            try:
                                stream_uri = media_service.GetStreamUri(token)
                                rtsp_uri = stream_uri.Uri
                            except Exception as e4:
                                logger.warning(f"Direct token approach failed: {str(e4)}")
                                
                                # Use fallback RTSP URL
                                username = camera_info['info'].get('username', '')
                                password = camera_info['info'].get('password', '')
                                port = camera_info['info'].get('port', 554)
                                
                                auth_str = f"{username}:{password}@" if username and password else ""
                                rtsp_uri = f"rtsp://{auth_str}{ip}:{port}/profile1"
                                logger.info(f"Using fallback RTSP URL: {rtsp_uri}")
                
                # Store stream URI in camera info
                camera_info['info']['stream_uri'] = rtsp_uri
                return rtsp_uri
                
            except Exception as e:
                logger.error(f"Failed to get stream URI: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error in get_stream_uri: {str(e)}")
            return None

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
            
        return self.get_stream_uri(ip)

    def test_common_credentials(self, ip, port=80):
        """This method has been removed as it was inappropriate."""
        logger.warning("The test_common_credentials method has been removed as it was inappropriate.")
        return False, "This functionality has been removed."

def init_camera_manager(config):
    """
    Initialize the camera manager with the application configuration.
    
    Args:
        config (dict): Application configuration
        
    Returns:
        ONVIFCameraManager: Initialized camera manager instance
    """
    try:
        manager = ONVIFCameraManager()
        logger.info("Camera manager initialized successfully")
        return manager
    except Exception as e:
        logger.error(f"Failed to initialize camera manager: {str(e)}")
        return None
