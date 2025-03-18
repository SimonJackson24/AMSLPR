#!/usr/bin/env python3
"""
Camera health monitoring module for AMSLPR system.

This module provides functionality to monitor camera health, attempt reconnection,
and notify administrators of camera issues.
"""

import time
import threading
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CameraHealthMonitor:
    """
    Monitor camera health and handle reconnection attempts.
    """
    
    def __init__(self, camera_manager, notification_manager=None, check_interval=60):
        """
        Initialize the camera health monitor.
        
        Args:
            camera_manager: The camera manager instance
            notification_manager: Optional notification manager for sending alerts
            check_interval: Interval in seconds between health checks
        """
        self.camera_manager = camera_manager
        self.notification_manager = notification_manager
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread = None
        self.camera_status = {}  # Tracks status of each camera
        self.reconnect_attempts = {}  # Tracks reconnection attempts
        self.max_reconnect_attempts = 5  # Maximum number of reconnection attempts
        self.reconnect_backoff = [30, 60, 120, 300, 600]  # Backoff times in seconds
    
    def start(self):
        """
        Start the health monitoring thread.
        """
        if self.running:
            logger.warning("Camera health monitor is already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Camera health monitor started")
    
    def stop(self):
        """
        Stop the health monitoring thread.
        """
        if not self.running:
            logger.warning("Camera health monitor is not running")
            return
        
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        logger.info("Camera health monitor stopped")
    
    def _monitor_loop(self):
        """
        Main monitoring loop.
        """
        while self.running:
            try:
                self._check_all_cameras()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in camera health monitor: {e}")
                time.sleep(10)  # Short delay before retrying after error
    
    def _check_all_cameras(self):
        """
        Check the health of all configured cameras.
        """
        # Get all cameras from the camera manager
        cameras = self.camera_manager.get_cameras()
        
        for camera_id, camera in cameras.items():
            self._check_camera(camera_id, camera)
    
    def _check_camera(self, camera_id, camera):
        """
        Check the health of a specific camera.
        
        Args:
            camera_id: ID of the camera to check
            camera: Camera configuration dictionary
        """
        # Skip cameras that are not supposed to be streaming
        if not self.camera_manager.should_be_streaming(camera_id):
            return
        
        # Check if the camera is streaming
        is_streaming = self.camera_manager.is_streaming(camera_id)
        
        # Get the last frame time
        last_frame_time = self.camera_manager.get_last_frame_time(camera_id)
        
        # Calculate time since last frame
        now = datetime.now()
        time_since_last_frame = None
        if last_frame_time:
            time_since_last_frame = (now - last_frame_time).total_seconds()
        
        # Determine camera health status
        if not is_streaming:
            status = "offline"
        elif time_since_last_frame and time_since_last_frame > 30:
            status = "stalled"  # Camera is streaming but not receiving frames
        else:
            status = "healthy"
        
        # Check if status has changed
        previous_status = self.camera_status.get(camera_id)
        if previous_status != status:
            self._handle_status_change(camera_id, camera, previous_status, status)
        
        # Update status
        self.camera_status[camera_id] = status
        
        # Handle reconnection if needed
        if status in ["offline", "stalled"]:
            self._handle_reconnection(camera_id, camera, status)
    
    def _handle_status_change(self, camera_id, camera, previous_status, new_status):
        """
        Handle a camera status change.
        
        Args:
            camera_id: ID of the camera
            camera: Camera configuration dictionary
            previous_status: Previous status of the camera
            new_status: New status of the camera
        """
        logger.info(f"Camera {camera_id} ({camera.get('name', 'Unknown')}) status changed from {previous_status or 'unknown'} to {new_status}")
        
        # Send notification if camera went offline or stalled
        if new_status in ["offline", "stalled"] and self.notification_manager:
            self._send_camera_alert(camera_id, camera, new_status)
        
        # Reset reconnection attempts if camera is now healthy
        if new_status == "healthy" and camera_id in self.reconnect_attempts:
            del self.reconnect_attempts[camera_id]
    
    def _handle_reconnection(self, camera_id, camera, status):
        """
        Handle reconnection attempts for a camera.
        
        Args:
            camera_id: ID of the camera
            camera: Camera configuration dictionary
            status: Current status of the camera
        """
        # Initialize reconnection attempts if not already tracking
        if camera_id not in self.reconnect_attempts:
            self.reconnect_attempts[camera_id] = {
                "count": 0,
                "next_attempt": datetime.now()
            }
        
        # Check if it's time for another reconnection attempt
        reconnect_info = self.reconnect_attempts[camera_id]
        if datetime.now() >= reconnect_info["next_attempt"]:
            # Increment attempt counter
            reconnect_info["count"] += 1
            
            # Log the reconnection attempt
            logger.info(f"Attempting to reconnect camera {camera_id} ({camera.get('name', 'Unknown')}), attempt {reconnect_info['count']}")
            
            # Try to restart the stream
            try:
                if self.camera_manager.is_streaming(camera_id):
                    self.camera_manager.stop_stream(camera_id)
                
                # Wait a moment before restarting
                time.sleep(2)
                
                # Start the stream again
                success = self.camera_manager.start_stream(camera_id)
                
                if success:
                    logger.info(f"Successfully reconnected camera {camera_id}")
                    # Status will be updated on next check if truly successful
                else:
                    logger.warning(f"Failed to reconnect camera {camera_id}")
            except Exception as e:
                logger.error(f"Error reconnecting camera {camera_id}: {e}")
            
            # Calculate next attempt time with exponential backoff
            backoff_index = min(reconnect_info["count"] - 1, len(self.reconnect_backoff) - 1)
            backoff_time = self.reconnect_backoff[backoff_index]
            reconnect_info["next_attempt"] = datetime.now() + timedelta(seconds=backoff_time)
            
            # If we've reached max attempts, give up and send a final notification
            if reconnect_info["count"] >= self.max_reconnect_attempts and self.notification_manager:
                self._send_reconnection_failed_alert(camera_id, camera)
    
    def _send_camera_alert(self, camera_id, camera, status):
        """
        Send an alert about a camera issue.
        
        Args:
            camera_id: ID of the camera
            camera: Camera configuration dictionary
            status: Current status of the camera
        """
        if not self.notification_manager:
            return
        
        camera_name = camera.get('name', 'Unknown')
        camera_location = camera.get('location', 'Unknown')
        
        subject = f"AMSLPR Camera Alert: {camera_name} is {status}"
        message = f"""Camera Alert

Camera: {camera_name}
Location: {camera_location}
Status: {status}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The system will attempt to reconnect automatically.
"""
        
        try:
            self.notification_manager.send_notification(subject, message, level="warning")
        except Exception as e:
            logger.error(f"Failed to send camera alert notification: {e}")
    
    def _send_reconnection_failed_alert(self, camera_id, camera):
        """
        Send an alert about failed reconnection attempts.
        
        Args:
            camera_id: ID of the camera
            camera: Camera configuration dictionary
        """
        if not self.notification_manager:
            return
        
        camera_name = camera.get('name', 'Unknown')
        camera_location = camera.get('location', 'Unknown')
        
        subject = f"AMSLPR Camera Alert: Failed to reconnect {camera_name}"
        message = f"""Camera Reconnection Failed

Camera: {camera_name}
Location: {camera_location}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The system has failed to reconnect to the camera after {self.max_reconnect_attempts} attempts.
Manual intervention may be required.
"""
        
        try:
            self.notification_manager.send_notification(subject, message, level="error")
        except Exception as e:
            logger.error(f"Failed to send reconnection failed notification: {e}")
    
    def get_camera_health_status(self):
        """
        Get the health status of all cameras.
        
        Returns:
            dict: Dictionary mapping camera IDs to their health status
        """
        return self.camera_status.copy()
    
    def get_camera_health_summary(self):
        """
        Get a summary of camera health.
        
        Returns:
            dict: Summary of camera health statistics
        """
        total = len(self.camera_status)
        healthy = sum(1 for status in self.camera_status.values() if status == "healthy")
        offline = sum(1 for status in self.camera_status.values() if status == "offline")
        stalled = sum(1 for status in self.camera_status.values() if status == "stalled")
        
        return {
            "total": total,
            "healthy": healthy,
            "offline": offline,
            "stalled": stalled,
            "health_percentage": (healthy / total * 100) if total > 0 else 0
        }
