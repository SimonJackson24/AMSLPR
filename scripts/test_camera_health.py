
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

#!/usr/bin/env python3
"""
Test script for camera health monitoring.

This script simulates camera health issues to test the monitoring system.
"""

import os
import sys
import time
import logging
import argparse
import threading
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import project modules
from src.recognition.onvif_camera import ONVIFCameraManager
from src.utils.camera_health import CameraHealthMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('AMSLPR.test')

class MockNotificationManager:
    """
    Mock notification manager for testing.
    """
    
    def __init__(self):
        self.notifications = []
    
    def send_notification(self, subject, message, level="info"):
        """
        Send a notification.
        
        Args:
            subject (str): Notification subject
            message (str): Notification message
            level (str): Notification level (info, warning, error)
        """
        notification = {
            'subject': subject,
            'message': message,
            'level': level,
            'time': datetime.now()
        }
        
        self.notifications.append(notification)
        logger.info(f"Notification sent: {subject} ({level})")
        logger.info(f"Message: {message}")

def simulate_camera_failure(camera_manager, camera_id, duration=60):
    """
    Simulate a camera failure.
    
    Args:
        camera_manager: Camera manager instance
        camera_id: ID of the camera to simulate failure for
        duration: Duration of the failure in seconds
    """
    logger.info(f"Simulating failure for camera {camera_id} for {duration} seconds")
    
    # Check if camera is streaming
    if not camera_manager.is_streaming(camera_id):
        logger.warning(f"Camera {camera_id} is not streaming, starting stream first")
        camera_manager.start_stream(camera_id)
        time.sleep(5)  # Wait for stream to start
    
    # Get current stream info
    stream_info = camera_manager.get_stream_info(camera_id)
    if not stream_info:
        logger.error(f"Failed to get stream info for camera {camera_id}")
        return
    
    logger.info(f"Current stream info: {stream_info}")
    
    # Stop the stream to simulate failure
    camera_manager.stop_stream(camera_id)
    logger.info(f"Stopped stream for camera {camera_id}")
    
    # Wait for the specified duration
    logger.info(f"Waiting for {duration} seconds...")
    time.sleep(duration)
    
    # Restart the stream
    logger.info(f"Restarting stream for camera {camera_id}")
    camera_manager.start_stream(camera_id)
    
    # Wait for stream to start
    time.sleep(5)
    
    # Get updated stream info
    stream_info = camera_manager.get_stream_info(camera_id)
    if stream_info:
        logger.info(f"Stream restarted successfully: {stream_info}")
    else:
        logger.error(f"Failed to restart stream for camera {camera_id}")

def simulate_stalled_camera(camera_manager, camera_id, duration=60):
    """
    Simulate a stalled camera (stream is active but no frames are being received).
    
    Args:
        camera_manager: Camera manager instance
        camera_id: ID of the camera to simulate stalling for
        duration: Duration of the stalling in seconds
    """
    logger.info(f"Simulating stalled camera {camera_id} for {duration} seconds")
    
    # Check if camera is streaming
    if not camera_manager.is_streaming(camera_id):
        logger.warning(f"Camera {camera_id} is not streaming, starting stream first")
        camera_manager.start_stream(camera_id)
        time.sleep(5)  # Wait for stream to start
    
    # Get current stream info
    stream_info = camera_manager.get_stream_info(camera_id)
    if not stream_info:
        logger.error(f"Failed to get stream info for camera {camera_id}")
        return
    
    logger.info(f"Current stream info: {stream_info}")
    
    # Modify the last frame time to simulate stalling
    if camera_id in camera_manager.streams:
        # Save the original last frame time
        original_last_frame_time = camera_manager.streams[camera_id]['last_frame_time']
        
        # Set the last frame time to a time in the past
        camera_manager.streams[camera_id]['last_frame_time'] = datetime.now() - timedelta(minutes=5)
        
        logger.info(f"Set last frame time to {camera_manager.streams[camera_id]['last_frame_time']}")
        
        # Wait for the specified duration
        logger.info(f"Waiting for {duration} seconds...")
        time.sleep(duration)
        
        # Restore the original last frame time
        camera_manager.streams[camera_id]['last_frame_time'] = original_last_frame_time
        
        logger.info(f"Restored last frame time to {camera_manager.streams[camera_id]['last_frame_time']}")
    else:
        logger.error(f"Camera {camera_id} stream not found")

def main():
    """
    Main function.
    """
    parser = argparse.ArgumentParser(description='Test camera health monitoring')
    parser.add_argument('--camera-id', type=str, help='ID of the camera to test')
    parser.add_argument('--failure-duration', type=int, default=60, help='Duration of simulated failure in seconds')
    parser.add_argument('--stall-duration', type=int, default=60, help='Duration of simulated stalling in seconds')
    parser.add_argument('--test-type', type=str, choices=['failure', 'stall', 'both'], default='both', help='Type of test to run')
    
    args = parser.parse_args()
    
    # Initialize camera manager
    camera_manager = ONVIFCameraManager()
    
    # Initialize notification manager
    notification_manager = MockNotificationManager()
    
    # Initialize camera health monitor
    health_monitor = CameraHealthMonitor(
        camera_manager=camera_manager,
        notification_manager=notification_manager,
        check_interval=10  # Check every 10 seconds for testing
    )
    
    # Start health monitor
    health_monitor.start()
    
    try:
        # Get camera ID to test
        camera_id = args.camera_id
        if not camera_id:
            # Get first camera from configuration
            cameras = camera_manager.get_cameras()
            if not cameras:
                logger.error("No cameras found in configuration")
                return
            
            camera_id = next(iter(cameras.keys()))
        
        logger.info(f"Using camera {camera_id} for testing")
        
        # Start camera stream if not already streaming
        if not camera_manager.is_streaming(camera_id):
            logger.info(f"Starting stream for camera {camera_id}")
            camera_manager.start_stream(camera_id)
            time.sleep(5)  # Wait for stream to start
        
        # Run tests
        if args.test_type in ['failure', 'both']:
            simulate_camera_failure(camera_manager, camera_id, args.failure_duration)
        
        if args.test_type in ['stall', 'both']:
            simulate_stalled_camera(camera_manager, camera_id, args.stall_duration)
        
        # Display notifications
        logger.info(f"Notifications sent: {len(notification_manager.notifications)}")
        for i, notification in enumerate(notification_manager.notifications):
            logger.info(f"Notification {i+1}:")
            logger.info(f"  Subject: {notification['subject']}")
            logger.info(f"  Level: {notification['level']}")
            logger.info(f"  Time: {notification['time']}")
        
        # Wait for a moment to allow health monitor to detect recovery
        logger.info("Waiting for health monitor to detect recovery...")
        time.sleep(20)
        
        # Display final health status
        health_status = health_monitor.get_camera_health_status()
        logger.info(f"Final health status: {health_status}")
        
        # Display health summary
        health_summary = health_monitor.get_camera_health_summary()
        logger.info(f"Health summary: {health_summary}")
    
    finally:
        # Stop health monitor
        health_monitor.stop()
        
        # Stop all streams
        camera_manager.stop_all_streams()

if __name__ == '__main__':
    main()
