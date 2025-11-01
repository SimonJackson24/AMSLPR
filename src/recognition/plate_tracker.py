#!/usr/bin/env python3
"""
License plate tracking module with Kalman filter and homography calculations.
Provides cross-camera license plate correlation and trajectory prediction.
"""

import cv2
import numpy as np
import logging
import time
import threading
from collections import defaultdict
from scipy.spatial.distance import cdist
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise

logger = logging.getLogger('VisiGate.plate_tracker')

class KalmanTracker:
    """
    Kalman filter for tracking license plate positions.
    """

    def __init__(self, initial_state, process_noise=1e-4, measurement_noise=1e-2):
        """
        Initialize Kalman tracker.

        Args:
            initial_state (numpy.ndarray): Initial state [x, y, vx, vy]
            process_noise (float): Process noise
            measurement_noise (float): Measurement noise
        """
        self.kf = KalmanFilter(dim_x=4, dim_z=2)

        # State: [x, y, vx, vy]
        self.kf.x = initial_state

        # State transition matrix
        self.kf.F = np.array([[1, 0, 1, 0],
                             [0, 1, 0, 1],
                             [0, 0, 1, 0],
                             [0, 0, 0, 1]])

        # Measurement matrix (we only measure position)
        self.kf.H = np.array([[1, 0, 0, 0],
                             [0, 1, 0, 0]])

        # Process noise
        self.kf.Q = Q_discrete_white_noise(dim=2, dt=1, var=process_noise)

        # Measurement noise
        self.kf.R = np.eye(2) * measurement_noise

        # Initial covariance
        self.kf.P = np.eye(4) * 100

    def predict(self):
        """
        Predict next state.

        Returns:
            numpy.ndarray: Predicted state
        """
        self.kf.predict()
        return self.kf.x

    def update(self, measurement):
        """
        Update with measurement.

        Args:
            measurement (numpy.ndarray): Measurement [x, y]
        """
        self.kf.update(measurement)

    def get_state(self):
        """
        Get current state.

        Returns:
            numpy.ndarray: Current state
        """
        return self.kf.x

    def get_position(self):
        """
        Get current position.

        Returns:
            tuple: (x, y)
        """
        return (self.kf.x[0], self.kf.x[1])

    def get_velocity(self):
        """
        Get current velocity.

        Returns:
            tuple: (vx, vy)
        """
        return (self.kf.x[2], self.kf.x[3])

class HomographyCalculator:
    """
    Homography matrix calculations for camera calibration.
    """

    def __init__(self):
        """
        Initialize homography calculator.
        """
        self.homography_matrices = {}  # (cam1, cam2) -> homography_matrix
        self.camera_positions = {}  # camera_id -> position_info

    def add_camera_calibration(self, camera_id, calibration_points):
        """
        Add camera calibration points.

        Args:
            camera_id (str): Camera identifier
            calibration_points (dict): Calibration points with world coordinates
        """
        self.camera_positions[camera_id] = calibration_points

    def calculate_homography(self, src_camera, dst_camera, min_points=4):
        """
        Calculate homography matrix between two cameras.

        Args:
            src_camera (str): Source camera ID
            dst_camera (str): Destination camera ID
            min_points (int): Minimum calibration points required

        Returns:
            numpy.ndarray: Homography matrix (3x3)
        """
        if src_camera not in self.camera_positions or dst_camera not in self.camera_positions:
            raise ValueError(f"Calibration data missing for cameras {src_camera} or {dst_camera}")

        src_points = self.camera_positions[src_camera]
        dst_points = self.camera_positions[dst_camera]

        # Find common calibration points
        common_points = set(src_points.keys()) & set(dst_points.keys())

        if len(common_points) < min_points:
            raise ValueError(f"Insufficient common calibration points: {len(common_points)} < {min_points}")

        # Extract point coordinates
        src_coords = []
        dst_coords = []

        for point_id in common_points:
            src_coord = src_points[point_id]['image_coord']
            dst_coord = dst_points[point_id]['image_coord']

            src_coords.append([src_coord[0], src_coord[1]])
            dst_coords.append([dst_coord[0], dst_coord[1]])

        src_coords = np.array(src_coords, dtype=np.float32)
        dst_coords = np.array(dst_coords, dtype=np.float32)

        # Calculate homography
        homography, mask = cv2.findHomography(src_coords, dst_coords, cv2.RANSAC, 5.0)

        if homography is None:
            raise ValueError("Failed to calculate homography matrix")

        # Store homography matrix
        self.homography_matrices[(src_camera, dst_camera)] = homography

        logger.info(f"Calculated homography between {src_camera} and {dst_camera}")
        return homography

    def transform_point(self, point, src_camera, dst_camera):
        """
        Transform point from source camera to destination camera.

        Args:
            point (tuple): Point coordinates (x, y)
            src_camera (str): Source camera ID
            dst_camera (str): Destination camera ID

        Returns:
            tuple: Transformed point coordinates
        """
        homography_key = (src_camera, dst_camera)

        if homography_key not in self.homography_matrices:
            # Try to calculate homography if not available
            try:
                self.calculate_homography(src_camera, dst_camera)
            except Exception as e:
                logger.error(f"Failed to calculate homography: {e}")
                return point

        homography = self.homography_matrices[homography_key]

        # Convert point to homogeneous coordinates
        point_homogeneous = np.array([[point[0], point[1], 1]], dtype=np.float32).T

        # Apply homography transformation
        transformed = homography @ point_homogeneous

        # Convert back to cartesian coordinates
        if transformed[2] != 0:
            transformed_point = (transformed[0] / transformed[2], transformed[1] / transformed[2])
        else:
            transformed_point = (transformed[0], transformed[1])

        return transformed_point

    def get_homography_matrix(self, src_camera, dst_camera):
        """
        Get homography matrix between cameras.

        Args:
            src_camera (str): Source camera ID
            dst_camera (str): Destination camera ID

        Returns:
            numpy.ndarray: Homography matrix
        """
        return self.homography_matrices.get((src_camera, dst_camera))

class LicensePlateTracker:
    """
    Main license plate tracking system.
    """

    def __init__(self, config):
        """
        Initialize license plate tracker.

        Args:
            config (dict): Tracking configuration
        """
        self.config = config
        self.trackers = {}  # plate_id -> KalmanTracker
        self.plate_history = defaultdict(list)  # plate_id -> list of detections
        self.cross_camera_correlations = {}  # (plate_text, camera_id) -> correlated_plates
        self.homography_calc = HomographyCalculator()

        # Configuration parameters
        self.max_track_age = config.get('max_track_age', 30)  # frames
        self.max_correlation_distance = config.get('max_correlation_distance', 50)  # pixels
        self.min_correlation_frames = config.get('min_correlation_frames', 3)
        self.prediction_horizon = config.get('prediction_horizon', 10)  # frames

        self.lock = threading.Lock()

    def update_track(self, plate_id, detection, camera_id):
        """
        Update tracking for a license plate.

        Args:
            plate_id (str): Unique plate identifier
            detection (dict): Detection data with position and timestamp
            camera_id (str): Camera identifier

        Returns:
            dict: Tracking information
        """
        with self.lock:
            position = (detection['x'] + detection['width'] / 2,
                       detection['y'] + detection['height'] / 2)
            timestamp = detection.get('timestamp', time.time())

            # Create new tracker if needed
            if plate_id not in self.trackers:
                initial_state = np.array([position[0], position[1], 0, 0])
                self.trackers[plate_id] = KalmanTracker(initial_state)

            # Update tracker
            self.trackers[plate_id].update(np.array(position))

            # Store detection history
            detection_info = {
                'position': position,
                'timestamp': timestamp,
                'camera_id': camera_id,
                'confidence': detection.get('confidence', 0.5),
                'bbox': (detection['x'], detection['y'], detection['width'], detection['height'])
            }

            self.plate_history[plate_id].append(detection_info)

            # Maintain history size
            if len(self.plate_history[plate_id]) > self.max_track_age:
                self.plate_history[plate_id].pop(0)

            # Predict next position
            predicted_state = self.trackers[plate_id].predict()
            predicted_position = (predicted_state[0], predicted_state[1])

            return {
                'plate_id': plate_id,
                'current_position': position,
                'predicted_position': predicted_position,
                'velocity': self.trackers[plate_id].get_velocity(),
                'track_length': len(self.plate_history[plate_id]),
                'camera_id': camera_id
            }

    def correlate_cross_camera(self, detections, camera_ids):
        """
        Correlate license plates across multiple cameras.

        Args:
            detections (dict): camera_id -> list of detections
            camera_ids (list): List of camera IDs

        Returns:
            dict: Correlation results
        """
        correlations = {}

        # Group detections by plate text
        plate_groups = defaultdict(lambda: defaultdict(list))

        for camera_id, camera_detections in detections.items():
            for detection in camera_detections:
                plate_text = detection.get('text', '')
                if plate_text:
                    plate_groups[plate_text][camera_id].append(detection)

        # Find correlations
        for plate_text, camera_detections in plate_groups.items():
            if len(camera_detections) < 2:
                continue  # Need at least 2 cameras

            correlation_key = (plate_text, tuple(sorted(camera_detections.keys())))

            # Calculate correlations between camera pairs
            camera_pairs = []
            for i, cam1 in enumerate(camera_detections.keys()):
                for cam2 in list(camera_detections.keys())[i+1:]:
                    correlation = self._calculate_camera_correlation(
                        camera_detections[cam1],
                        camera_detections[cam2],
                        cam1, cam2
                    )
                    if correlation:
                        camera_pairs.append((cam1, cam2, correlation))

            if camera_pairs:
                correlations[correlation_key] = camera_pairs

        return correlations

    def _calculate_camera_correlation(self, detections1, detections2, cam1, cam2):
        """
        Calculate correlation between detections from two cameras.

        Args:
            detections1 (list): Detections from camera 1
            detections2 (list): Detections from camera 2
            cam1 (str): Camera 1 ID
            cam2 (str): Camera 2 ID

        Returns:
            dict: Correlation information
        """
        if not detections1 or not detections2:
            return None

        # Transform positions using homography if available
        transformed_positions1 = []
        for det in detections1:
            pos = (det['x'] + det['width']/2, det['y'] + det['height']/2)
            transformed_pos = self.homography_calc.transform_point(pos, cam1, cam2)
            transformed_positions1.append(transformed_pos)

        positions2 = []
        for det in detections2:
            pos = (det['x'] + det['width']/2, det['y'] + det['height']/2)
            positions2.append(pos)

        # Calculate distances between all pairs
        if transformed_positions1 and positions2:
            distances = cdist(transformed_positions1, positions2)

            # Find minimum distance pairs
            min_distance = np.min(distances)
            min_indices = np.unravel_index(np.argmin(distances), distances.shape)

            if min_distance <= self.max_correlation_distance:
                return {
                    'distance': min_distance,
                    'detection1': detections1[min_indices[0]],
                    'detection2': detections2[min_indices[1]],
                    'transformed_position': transformed_positions1[min_indices[0]]
                }

        return None

    def predict_trajectory(self, plate_id, frames_ahead=10):
        """
        Predict license plate trajectory.

        Args:
            plate_id (str): Plate identifier
            frames_ahead (int): Number of frames to predict

        Returns:
            list: Predicted positions
        """
        if plate_id not in self.trackers:
            return []

        tracker = self.trackers[plate_id]
        predictions = []

        # Save current state
        current_state = tracker.get_state().copy()

        for _ in range(frames_ahead):
            # Predict next position
            predicted_state = tracker.predict()
            predictions.append((predicted_state[0], predicted_state[1]))

        # Restore state
        tracker.kf.x = current_state

        return predictions

    def get_tracking_stats(self):
        """
        Get tracking statistics.

        Returns:
            dict: Tracking statistics
        """
        with self.lock:
            return {
                'active_tracks': len(self.trackers),
                'total_detections': sum(len(history) for history in self.plate_history.values()),
                'correlations_found': len(self.cross_camera_correlations),
                'homography_matrices': len(self.homography_calc.homography_matrices)
            }

    def cleanup_old_tracks(self):
        """
        Clean up old tracks that haven't been updated recently.
        """
        current_time = time.time()
        tracks_to_remove = []

        with self.lock:
            for plate_id, history in self.plate_history.items():
                if history:
                    last_update = history[-1]['timestamp']
                    if current_time - last_update > self.max_track_age:
                        tracks_to_remove.append(plate_id)

            for plate_id in tracks_to_remove:
                del self.trackers[plate_id]
                del self.plate_history[plate_id]

        if tracks_to_remove:
            logger.info(f"Cleaned up {len(tracks_to_remove)} old tracks")

    def add_homography_calibration(self, camera_id, calibration_points):
        """
        Add homography calibration for a camera.

        Args:
            camera_id (str): Camera identifier
            calibration_points (dict): Calibration points
        """
        self.homography_calc.add_camera_calibration(camera_id, calibration_points)