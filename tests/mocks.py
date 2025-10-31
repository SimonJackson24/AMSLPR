#!/usr/bin/env python3
"""
Mock objects and utilities for AMSLPR testing.
"""

import numpy as np
from unittest.mock import Mock, MagicMock
import cv2


class MockONVIFCamera:
    """Mock ONVIF camera for testing."""

    def __init__(self, frame_width=640, frame_height=480, return_none=False):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.return_none = return_none
        self.frame_count = 0
        self.stream_started = False

    def start_stream(self, camera_id):
        """Mock start stream."""
        self.stream_started = True
        return True

    def get_frame(self, camera_id):
        """Mock get frame."""
        if self.return_none:
            return None, None

        self.frame_count += 1
        # Create a simple test frame
        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)

        # Add some content that might be detected as a plate
        if self.frame_count % 3 == 0:  # Every third frame has a plate
            cv2.rectangle(frame, (200, 200), (400, 250), (255, 255, 255), -1)
            cv2.putText(frame, "ABC123", (220, 235), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        timestamp = 1234567890.0 + self.frame_count * 0.1
        return frame, timestamp

    def stop_stream(self, camera_id):
        """Mock stop stream."""
        self.stream_started = False
        return True


class MockCacheManager:
    """Mock cache manager for testing."""

    def __init__(self, enabled=True, hit_rate=0.8):
        self.enabled = enabled
        self.hit_rate = hit_rate
        self.cache = {}
        self.stats = {
            'result_cache': {'hits': 0, 'misses': 0},
            'memory': {'size': 0},
            'redis': {'connected': False},
            'file': {'size': 0}
        }

    def get_ocr_result(self, image):
        """Mock get OCR result."""
        if not self.enabled:
            return None

        # Simple cache key based on image shape
        key = f"{image.shape}_{hash(image.tobytes()) % 1000}"

        if key in self.cache and np.random.rand() < self.hit_rate:
            self.stats['result_cache']['hits'] += 1
            return self.cache[key]
        else:
            self.stats['result_cache']['misses'] += 1
            return None

    def cache_ocr_result(self, image, text, confidence):
        """Mock cache OCR result."""
        if not self.enabled:
            return False

        key = f"{image.shape}_{hash(image.tobytes()) % 1000}"
        self.cache[key] = Mock(text=text, confidence=confidence)
        return True

    def get_stats(self):
        """Mock get stats."""
        return self.stats.copy()

    def health_check(self):
        """Mock health check."""
        return {
            'memory': {'healthy': True},
            'redis': {'healthy': self.stats['redis']['connected']},
            'file': {'healthy': True}
        }


class MockOCRModel:
    """Mock OCR model for testing."""

    def __init__(self, model_type='tensorflow', char_map=None):
        self.model_type = model_type
        self.char_map = char_map or {i: chr(65 + i) for i in range(26)}

    def predict(self, input_data, verbose=0):
        """Mock predict method."""
        batch_size, height, width = input_data.shape[:3]
        time_steps = 20  # Typical CTC time steps
        num_classes = len(self.char_map)

        # Generate random predictions with some structure
        output = np.random.rand(batch_size, time_steps, num_classes)

        # Make some predictions more likely (simulate learned patterns)
        for i in range(min(5, len(self.char_map))):  # First few characters more likely
            output[:, :, i] += 0.5

        return output

    def get_input_names(self):
        """Mock get input names for Hailo."""
        return ['input_1']

    def get_output_names(self):
        """Mock get output names for Hailo."""
        return ['output_1']


class MockHailoDevice:
    """Mock Hailo device for testing."""

    def __init__(self):
        self.models = {}

    def load_model(self, model_path):
        """Mock load model."""
        model = MockOCRModel('hailo')
        self.models[model_path] = model
        return model

    def run(self, model, inputs):
        """Mock run inference."""
        # Simulate Hailo inference
        input_data = inputs[0].get_data()
        output = model.predict(input_data)
        mock_output = Mock()
        mock_output.get_data.return_value = output
        return [mock_output]


class MockInput:
    """Mock Hailo input."""

    def __init__(self, name, data):
        self.name = name
        self.data = data

    def get_data(self):
        """Get input data."""
        return self.data


def create_test_plate_image(text="ABC123", width=200, height=50):
    """Create a test license plate image."""
    # Create blank image
    image = np.ones((height, width, 3), dtype=np.uint8) * 255  # White background

    # Add text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = min(width, height) / 200  # Scale font to image size
    thickness = max(1, int(height / 20))

    # Center the text
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2

    cv2.putText(image, text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness)

    # Add some noise to make it more realistic
    noise = np.random.randint(0, 50, image.shape, dtype=np.uint8)
    image = cv2.add(image, noise)

    return image


def create_corrupted_frame(width=640, height=480):
    """Create a corrupted/invalid frame for testing."""
    # Create frame with invalid data
    frame = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    # Make some parts completely black
    frame[100:200, 100:200] = 0
    # Add extreme brightness
    frame[300:400, 300:400] = 255
    return frame


def mock_pytesseract_results(results):
    """Context manager to mock pytesseract results."""
    from unittest.mock import patch

    def side_effect(image, config=None, **kwargs):
        if isinstance(results, list):
            return results.pop(0) if results else ""
        return results

    return patch('pytesseract.image_to_string', side_effect=side_effect)


def mock_tensorflow_availability(available=True):
    """Context manager to mock TensorFlow availability."""
    return patch('src.recognition.detector_fixed.TENSORFLOW_AVAILABLE', available)


def mock_hailo_availability(available=True):
    """Context manager to mock Hailo availability."""
    return patch('src.recognition.detector_fixed.HAILO_AVAILABLE', available)


class MockThreadPoolExecutor:
    """Mock thread pool executor that runs tasks synchronously."""

    def __init__(self, max_workers=None):
        self.max_workers = max_workers
        self.tasks = []

    def submit(self, fn, *args, **kwargs):
        """Submit task and return future."""
        future = Mock()
        try:
            result = fn(*args, **kwargs)
            future.result.return_value = result
        except Exception as e:
            future.result.side_effect = e
        return future

    def shutdown(self, wait=True):
        """Shutdown executor."""
        pass


def create_performance_test_data(num_frames=100, frame_size=(480, 640, 3)):
    """Create test data for performance testing."""
    frames = []
    for i in range(num_frames):
        frame = np.random.randint(0, 256, frame_size, dtype=np.uint8)
        # Add a plate to some frames
        if i % 10 == 0:
            cv2.rectangle(frame, (200, 200), (400, 250), (255, 255, 255), -1)
        frames.append(frame)
    return frames


def mock_environment_variables(**kwargs):
    """Context manager to mock environment variables."""
    from unittest.mock import patch
    import os

    original_values = {}
    for key in kwargs:
        original_values[key] = os.environ.get(key)

    def get_env(key, default=None):
        return kwargs.get(key, original_values.get(key, default))

    with patch.dict(os.environ, kwargs):
        yield


def create_test_config_variations():
    """Create various test configurations for comprehensive testing."""
    configs = []

    # Basic config
    configs.append({
        'camera_id': 0,
        'frame_width': 640,
        'frame_height': 480,
        'confidence_threshold': 0.7,
        'save_images': False,
        'use_onvif': False,
        'mock_mode': True,
        'ocr_method': 'tesseract'
    })

    # Config with caching enabled
    config_cache = configs[0].copy()
    config_cache.update({
        'cache': {
            'enabled': True,
            'memory': {'max_size': 100},
            'redis': {'enabled': False},
            'file': {'enabled': True}
        }
    })
    configs.append(config_cache)

    # Config with parallel processing
    config_parallel = configs[0].copy()
    config_parallel.update({
        'performance': {
            'enable_parallel': True,
            'max_workers': 4
        }
    })
    configs.append(config_parallel)

    # Config with deep learning OCR
    config_dl = configs[0].copy()
    config_dl.update({
        'ocr_method': 'deep_learning',
        'use_hailo_tpu': False
    })
    configs.append(config_dl)

    # Config with Hailo TPU
    config_hailo = configs[0].copy()
    config_hailo.update({
        'ocr_method': 'deep_learning',
        'use_hailo_tpu': True
    })
    configs.append(config_hailo)

    return configs