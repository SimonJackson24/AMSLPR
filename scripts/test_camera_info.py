#!/usr/bin/env python3

'''
Test script to retrieve camera information using ONVIF
'''

import sys
import os
import logging
from onvif.client import ONVIFCamera

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CameraTest')

def get_camera_info(ip, port, username, password):
    '''
    Connect to a camera and retrieve its information
    '''
    try:
        # Get the path to the WSDL directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        wsdl_dir = os.path.join(project_root, 'src', 'recognition', 'wsdl')
        
        logger.info(f"Connecting to camera at {ip}:{port} with WSDL path: {wsdl_dir}")
        
        # Create camera with explicit WSDL files
        camera = ONVIFCamera(
            ip, 
            port,
            username, 
            password,
            wsdl_dir,
            encrypt=True
        )
        
        # Get device information
        device_info = camera.devicemgmt.GetDeviceInformation()
        logger.info(f"Device info: {device_info}")
        
        # Print all device info fields
        print("\nCamera Information:")
        print(f"Manufacturer: {device_info.get('Manufacturer', 'Unknown')}")
        print(f"Model: {device_info.get('Model', 'Unknown')}")
        print(f"FirmwareVersion: {device_info.get('FirmwareVersion', 'Unknown')}")
        print(f"SerialNumber: {device_info.get('SerialNumber', 'Unknown')}")
        print(f"HardwareId: {device_info.get('HardwareId', 'Unknown')}")
        
        return device_info
        
    except Exception as e:
        logger.error(f"Error retrieving camera info: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python test_camera_info.py <ip> <port> <username> <password>")
        sys.exit(1)
        
    ip = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = sys.argv[4]
    
    get_camera_info(ip, port, username, password)
