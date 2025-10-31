#!/usr/bin/env python3
"""
Camera synchronization module for multi-camera license plate recognition.
Provides NTP-based timestamp synchronization and frame alignment.
"""

import time
import logging
import threading
import socket
import struct
import ntplib
from datetime import datetime, timezone
import cv2
import numpy as np

logger = logging.getLogger('AMSLPR.camera_sync')

class NTPSynchronizer:
    """
    NTP-based time synchronization for cameras.
    """

    def __init__(self, ntp_servers=None, sync_interval=300):
        """
        Initialize NTP synchronizer.

        Args:
            ntp_servers (list): List of NTP server addresses
            sync_interval (int): Synchronization interval in seconds
        """
        self.ntp_servers = ntp_servers or [
            'pool.ntp.org',
            'time.nist.gov',
            'time.google.com'
        ]
        self.sync_interval = sync_interval
        self.offset = 0.0  # Time offset from NTP server
        self.last_sync = 0
        self.lock = threading.Lock()
        self.client = ntplib.NTPClient()

    def get_ntp_time(self):
        """
        Get current time from NTP server.

        Returns:
            float: NTP timestamp
        """
        for server in self.ntp_servers:
            try:
                response = self.client.request(server, timeout=5)
                return response.tx_time
            except Exception as e:
                logger.warning(f"Failed to sync with NTP server {server}: {e}")
                continue
        logger.error("Failed to sync with any NTP server")
        return time.time()

    def sync_time(self):
        """
        Synchronize local time with NTP server.

        Returns:
            float: Time offset
        """
        ntp_time = self.get_ntp_time()
        local_time = time.time()
        self.offset = ntp_time - local_time

        with self.lock:
            self.last_sync = time.time()

        logger.info(f"Time synchronized with offset: {self.offset:.6f}s")
        return self.offset

    def get_synchronized_time(self):
        """
        Get synchronized timestamp.

        Returns:
            float: Synchronized timestamp
        """
        current_time = time.time()

        # Check if we need to resync
        if current_time - self.last_sync > self.sync_interval:
            self.sync_time()

        return current_time + self.offset

class FrameSynchronizer:
    """
    Frame synchronization for multi-camera setups.
    """

    def __init__(self, max_drift=0.1, buffer_size=30):
        """
        Initialize frame synchronizer.

        Args:
            max_drift (float): Maximum allowed time drift in seconds
            buffer_size (int): Size of frame buffer for each camera
        """
        self.max_drift = max_drift
        self.buffer_size = buffer_size
        self.cameras = {}  # camera_id -> frame_buffer
        self.timestamps = {}  # camera_id -> timestamp_buffer
        self.lock = threading.Lock()

    def add_frame(self, camera_id, frame, timestamp):
        """
        Add frame to synchronization buffer.

        Args:
            camera_id (str): Camera identifier
            frame (numpy.ndarray): Frame data
            timestamp (float): Frame timestamp
        """
        with self.lock:
            if camera_id not in self.cameras:
                self.cameras[camera_id] = []
                self.timestamps[camera_id] = []

            # Add frame to buffer
            self.cameras[camera_id].append(frame)
            self.timestamps[camera_id].append(timestamp)

            # Maintain buffer size
            if len(self.cameras[camera_id]) > self.buffer_size:
                self.cameras[camera_id].pop(0)
                self.timestamps[camera_id].pop(0)

    def get_synchronized_frames(self, target_time):
        """
        Get synchronized frames closest to target time.

        Args:
            target_time (float): Target timestamp

        Returns:
            dict: camera_id -> synchronized_frame
        """
        synchronized_frames = {}

        with self.lock:
            for camera_id, timestamps in self.timestamps.items():
                if not timestamps:
                    continue

                # Find closest timestamp
                closest_idx = min(range(len(timestamps)),
                                key=lambda i: abs(timestamps[i] - target_time))

                # Check if within acceptable drift
                if abs(timestamps[closest_idx] - target_time) <= self.max_drift:
                    synchronized_frames[camera_id] = self.cameras[camera_id][closest_idx]

        return synchronized_frames

    def get_frame_drift(self, camera_id, reference_time):
        """
        Calculate frame drift for a camera.

        Args:
            camera_id (str): Camera identifier
            reference_time (float): Reference timestamp

        Returns:
            float: Time drift in seconds
        """
        with self.lock:
            if camera_id not in self.timestamps or not self.timestamps[camera_id]:
                return float('inf')

            timestamps = self.timestamps[camera_id]
            closest_time = min(timestamps, key=lambda t: abs(t - reference_time))
            return abs(closest_time - reference_time)

class CameraSyncManager:
    """
    Main camera synchronization manager.
    """

    def __init__(self, config):
        """
        Initialize camera sync manager.

        Args:
            config (dict): Synchronization configuration
        """
        self.config = config
        self.ntp_sync = NTPSynchronizer(
            ntp_servers=config.get('ntp_servers'),
            sync_interval=config.get('sync_interval', 300)
        )
        self.frame_sync = FrameSynchronizer(
            max_drift=config.get('max_drift', 0.1),
            buffer_size=config.get('buffer_size', 30)
        )
        self.camera_offsets = {}  # camera_id -> time_offset
        self.lock = threading.Lock()

    def synchronize_cameras(self, camera_ids):
        """
        Synchronize multiple cameras.

        Args:
            camera_ids (list): List of camera IDs to synchronize

        Returns:
            dict: Synchronization results
        """
        results = {}

        # Get NTP time as reference
        ntp_time = self.ntp_sync.get_synchronized_time()

        for camera_id in camera_ids:
            try:
                # Calculate camera offset (this would typically involve
                # querying the camera's internal clock)
                camera_time = self._get_camera_time(camera_id)
                offset = camera_time - ntp_time

                with self.lock:
                    self.camera_offsets[camera_id] = offset

                results[camera_id] = {
                    'offset': offset,
                    'status': 'synchronized'
                }

                logger.info(f"Camera {camera_id} synchronized with offset: {offset:.6f}s")

            except Exception as e:
                logger.error(f"Failed to synchronize camera {camera_id}: {e}")
                results[camera_id] = {
                    'offset': 0.0,
                    'status': 'failed',
                    'error': str(e)
                }

        return results

    def _get_camera_time(self, camera_id):
        """
        Get camera's current time (placeholder - would query actual camera).

        Args:
            camera_id (str): Camera identifier

        Returns:
            float: Camera timestamp
        """
        # In a real implementation, this would query the camera's NTP time
        # For now, return current time with some simulated drift
        return time.time() + np.random.normal(0, 0.01)

    def get_synchronized_timestamp(self, camera_id, local_timestamp):
        """
        Get synchronized timestamp for a camera.

        Args:
            camera_id (str): Camera identifier
            local_timestamp (float): Local timestamp from camera

        Returns:
            float: Synchronized timestamp
        """
        with self.lock:
            offset = self.camera_offsets.get(camera_id, 0.0)
            return local_timestamp - offset

    def add_frame_for_sync(self, camera_id, frame, timestamp):
        """
        Add frame for synchronization.

        Args:
            camera_id (str): Camera identifier
            frame (numpy.ndarray): Frame data
            timestamp (float): Frame timestamp
        """
        sync_timestamp = self.get_synchronized_timestamp(camera_id, timestamp)
        self.frame_sync.add_frame(camera_id, frame, sync_timestamp)

    def get_synchronized_frameset(self, target_time=None):
        """
        Get synchronized frame set from all cameras.

        Args:
            target_time (float, optional): Target time, uses current if None

        Returns:
            dict: Synchronized frames
        """
        if target_time is None:
            target_time = self.ntp_sync.get_synchronized_time()

        return self.frame_sync.get_synchronized_frames(target_time)

    def get_sync_status(self):
        """
        Get synchronization status.

        Returns:
            dict: Status information
        """
        with self.lock:
            return {
                'ntp_offset': self.ntp_sync.offset,
                'last_sync': self.ntp_sync.last_sync,
                'camera_offsets': self.camera_offsets.copy(),
                'buffer_sizes': {
                    cam_id: len(self.frame_sync.cameras.get(cam_id, []))
                    for cam_id in self.camera_offsets.keys()
                }
            }