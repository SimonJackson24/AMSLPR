
# VisiGate - Vision-Based Access Control System
# Copyright (c) 2025 VisiGate. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Test script for ONVIF camera integration.

This script tests the ONVIF camera manager by discovering cameras on the network,
connecting to a specified camera, and displaying a live video feed.
"""

import os
import sys
import cv2
import time
import json
import logging
import argparse
from datetime import datetime

# Add the parent directory to the path so we can import the src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.recognition.onvif_camera import ONVIFCameraManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VisiGate.test_onvif')

def load_config(config_path):
    """
    Load configuration from a JSON file.
    
    Args:
        config_path (str): Path to the configuration file
        
    Returns:
        dict: Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}

def discover_cameras(camera_manager):
    """
    Discover ONVIF cameras on the network.
    
    Args:
        camera_manager (ONVIFCameraManager): ONVIF camera manager instance
    """
    logger.info("Discovering ONVIF cameras...")
    discovered_cameras = camera_manager.discover_cameras()
    
    if discovered_cameras:
        logger.info(f"Discovered {len(discovered_cameras)} cameras:")
        for i, camera in enumerate(discovered_cameras):
            logger.info(f"  {i+1}. {camera['name']} at {camera['ip']}:{camera['port']}")
    else:
        logger.info("No cameras discovered")

def test_camera(camera_manager, camera_id):
    """
    Test a specific camera by displaying its video feed.
    
    Args:
        camera_manager (ONVIFCameraManager): ONVIF camera manager instance
        camera_id (str): ID of the camera to test
    """
    # Check if camera exists
    camera = camera_manager.get_camera(camera_id)
    if not camera:
        logger.error(f"Camera {camera_id} not found")
        return
    
    logger.info(f"Testing camera {camera_id} ({camera['name']}) at {camera['ip']}:{camera['port']}")
    
    # Start streaming
    if not camera_manager.start_stream(camera_id):
        logger.error(f"Failed to start stream for camera {camera_id}")
        return
    
    logger.info("Stream started. Press 'q' to quit.")
    
    try:
        # Display video feed
        while True:
            frame, timestamp = camera_manager.get_frame(camera_id)
            if frame is None:
                logger.warning("No frame received")
                time.sleep(0.1)
                continue
            
            # Add timestamp to frame
            cv2.putText(
                frame,
                timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )
            
            # Display frame
            cv2.imshow(f"Camera {camera_id} - {camera['name']}", frame)
            
            # Check for quit key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        logger.info("Test interrupted")
    finally:
        # Clean up
        cv2.destroyAllWindows()
        camera_manager.stop_stream(camera_id)
        logger.info("Stream stopped")

def main():
    """
    Main function.
    """
    parser = argparse.ArgumentParser(description='Test ONVIF camera integration')
    parser.add_argument('--config', default='config/config.json', help='Path to configuration file')
    parser.add_argument('--camera', help='Camera ID to test')
    parser.add_argument('--discover', action='store_true', help='Discover cameras on the network')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        logger.error("Failed to load configuration")
        return 1
    
    # Initialize camera manager
    camera_manager = ONVIFCameraManager(config.get('camera', {}))
    
    # Discover cameras if requested
    if args.discover:
        discover_cameras(camera_manager)
    
    # Test specific camera if provided
    if args.camera:
        test_camera(camera_manager, args.camera)
    
    # Clean up
    camera_manager.cleanup()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
