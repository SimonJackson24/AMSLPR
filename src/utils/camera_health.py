#!/usr/bin/env python3
"""
Camera health monitoring module.
Monitors camera status and sends notifications for issues.
"""

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('AMSLPR.utils.camera_health')

class AsyncCameraHealthMonitor:
    """
    Asynchronous monitor for camera health status.
    Checks camera streams and sends notifications for issues.
    """
    
    def __init__(self, camera_manager, notification_manager=None, check_interval=60):
        """
        Initialize the camera health monitor.
        
        Args:
            camera_manager (ONVIFCameraManager): Camera manager instance
            notification_manager (NotificationManager, optional): Notification manager instance
            check_interval (int): Interval between health checks in seconds
        """
        self.camera_manager = camera_manager
        self.notification_manager = notification_manager
        self.check_interval = check_interval
        self.running = False
        self.task = None
        self.camera_status = {}
        
        # Health check thresholds
        self.stall_threshold = timedelta(seconds=10)  # Camera considered stalled if no frames for 10s
        self.offline_threshold = timedelta(seconds=30)  # Camera considered offline if no frames for 30s
    
    async def start(self):
        """Start the health monitor."""
        if self.running:
            logger.warning("Health monitor already running")
            return
        
        try:
            self.running = True
            self.task = asyncio.create_task(self._monitor_loop())
            logger.info("Camera health monitor started")
        except Exception as e:
            self.running = False
            logger.error(f"Failed to start camera health monitor: {e}")
            raise
    
    async def stop(self):
        """Stop the health monitor and cleanup resources."""
        if not self.running:
            return
        
        try:
            self.running = False
            if self.task:
                # Give the task a chance to complete gracefully
                try:
                    await asyncio.wait_for(self.task, timeout=5.0)
                except asyncio.TimeoutError:
                    # Force cancel if it doesn't complete in time
                    self.task.cancel()
                    try:
                        await self.task
                    except asyncio.CancelledError:
                        pass
                self.task = None
            
            # Clean up camera status
            self.camera_status.clear()
            logger.info("Camera health monitor stopped and cleaned up")
        except Exception as e:
            logger.error(f"Error during health monitor shutdown: {e}")
            raise
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self._check_cameras()
            except Exception as e:
                logger.error(f"Error in camera health check: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def _check_cameras(self):
        """Check health status of all cameras."""
        cameras = self.camera_manager.get_all_cameras()
        current_time = datetime.now()
        
        for camera_id, camera in cameras.items():
            try:
                # Skip cameras that are intentionally disabled
                if not camera.get('enabled', True):
                    continue
                
                # Get camera status
                old_status = self.camera_status.get(camera_id, {}).get('status', 'unknown')
                new_status = await self._check_camera_health(camera_id, camera, current_time)
                
                # Update status
                self.camera_status[camera_id] = {
                    'status': new_status,
                    'last_check': current_time,
                    'camera': camera
                }
                
                # Send notification if status changed to worse
                if self._should_notify(old_status, new_status):
                    await self._send_notification(camera_id, camera, new_status)
                
            except Exception as e:
                logger.error(f"Error checking camera {camera_id}: {e}")
    
    async def _check_camera_health(self, camera_id, camera, current_time):
        """
        Check health of a specific camera.
        
        Args:
            camera_id (str): Camera identifier
            camera (dict): Camera information
            current_time (datetime): Current time for comparison
        
        Returns:
            str: Health status ('healthy', 'stalled', 'offline', or 'error')
        """
        try:
            # Try to get camera status
            stream_url = self.camera_manager.get_stream_url(camera_id)
            if not stream_url:
                return 'offline'
            
            # Check if we can connect to the camera
            camera_info = self.camera_manager.get_camera_info(camera_id)
            if not camera_info:
                return 'offline'
            
            # Check if we can get camera imaging settings
            try:
                imaging_service = camera_info.get('imaging_service')
                if imaging_service:
                    video_source_token = camera_info.get('video_source_token')
                    if video_source_token:
                        await imaging_service.GetImagingSettings({'VideoSourceToken': video_source_token})
            except Exception as e:
                logger.warning(f"Could not get imaging settings for camera {camera_id}: {e}")
                return 'error'
            
            return 'healthy'
            
        except Exception as e:
            logger.error(f"Error checking camera {camera_id} health: {e}")
            return 'error'
    
    def _should_notify(self, old_status, new_status):
        """
        Determine if a notification should be sent based on status change.
        
        Args:
            old_status (str): Previous camera status
            new_status (str): New camera status
        
        Returns:
            bool: True if notification should be sent
        """
        # Status severity order (higher index = worse)
        severity = ['healthy', 'stalled', 'error', 'offline']
        
        # Get severity indices
        old_severity = severity.index(old_status) if old_status in severity else -1
        new_severity = severity.index(new_status) if new_status in severity else -1
        
        # Notify if status got worse
        return new_severity > old_severity
    
    async def _send_notification(self, camera_id, camera, status):
        """
        Send a notification about camera health status.
        
        Args:
            camera_id (str): Camera identifier
            camera (dict): Camera information
            status (str): New camera status
        """
        if not self.notification_manager:
            return
        
        message = (
            f"Camera {camera.get('name', camera_id)} is {status}.\n"
            f"Location: {camera.get('location', 'Unknown')}\n"
            f"IP: {camera.get('ip', 'Unknown')}"
        )
        
        try:
            await self.notification_manager.send_notification(
                title=f"Camera Health Alert - {camera.get('name', camera_id)}",
                message=message,
                level='warning' if status == 'stalled' else 'error'
            )
        except Exception as e:
            logger.error(f"Error sending camera health notification: {e}")
    
    def get_camera_health_status(self):
        """Get current health status for all cameras."""
        return {
            camera_id: status['status']
            for camera_id, status in self.camera_status.items()
        }
    
    def get_camera_health_summary(self):
        """Get summary of camera health status."""
        total = len(self.camera_status)
        healthy = sum(1 for s in self.camera_status.values() if s['status'] == 'healthy')
        stalled = sum(1 for s in self.camera_status.values() if s['status'] == 'stalled')
        offline = sum(1 for s in self.camera_status.values() if s['status'] == 'offline')
        error = sum(1 for s in self.camera_status.values() if s['status'] == 'error')
        
        return {
            'total': total,
            'healthy': healthy,
            'stalled': stalled,
            'offline': offline,
            'error': error,
            'health_percentage': (healthy / total * 100) if total > 0 else 0
        }
