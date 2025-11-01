#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for VisiGate testing.
"""

import pytest
import numpy as np
import cv2
import tempfile
import os
import sys
from unittest.mock import Mock, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def basic_config():
    """Basic configuration for testing."""
    return {
        'camera_id': 0,
        'frame_width': 640,
        'frame_height': 480,
        'confidence_threshold': 0.7,
        'save_images': False,
        'image_save_path': 'data/images',
        'use_onvif': False,
        'mock_mode': True,
        'ocr_method': 'tesseract',
        'performance': {
            'enable_buffer_prealloc': True,
            'enable_parallel': False,
            'max_workers': 2,
            'enable_monitoring': True
        },
        'cache': {
            'enabled': False,
            'memory': {'max_size': 1000, 'default_ttl': 300},
            'redis': {'enabled': False},
            'file': {'enabled': True, 'cache_dir': 'cache/detector'}
        }
    }


@pytest.fixture
def sample_frame():
    """Create a sample frame for testing."""
    # Create a simple test frame with some shapes
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add a white rectangle that could be mistaken for a license plate
    cv2.rectangle(frame, (200, 200), (400, 250), (255, 255, 255), -1)
    # Add some noise
    cv2.circle(frame, (300, 220), 10, (128, 128, 128), -1)
    return frame


@pytest.fixture
def mock_onvif_manager():
    """Mock ONVIF camera manager."""
    mock_manager = Mock()
    mock_manager.get_frame.return_value = (np.zeros((480, 640, 3), dtype=np.uint8), 1234567890.0)
    mock_manager.start_stream.return_value = True
    return mock_manager


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager."""
    mock_cache = Mock()
    mock_cache.get_ocr_result.return_value = None
    mock_cache.cache_ocr_result.return_value = True
    mock_cache.get_stats.return_value = {
        'result_cache': {'hits': 10, 'misses': 5},
        'memory': {'size': 1024},
        'redis': {'connected': False},
        'file': {'size': 2048}
    }
    mock_cache.health_check.return_value = {
        'memory': {'healthy': True},
        'redis': {'healthy': True},
        'file': {'healthy': True}
    }
    return mock_cache


@pytest.fixture
def mock_tesseract():
    """Mock pytesseract for testing."""
    with pytest.mock.patch('pytesseract.image_to_string') as mock_tess:
        mock_tess.return_value = "ABC123"
        yield mock_tess


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_plate():
    """Sample license plate data."""
    return {
        'x': 200,
        'y': 200,
        'width': 200,
        'height': 50,
        'confidence': 0.85
    }


@pytest.fixture
def ocr_config():
    """OCR configuration for testing."""
    return {
        'ocr_method': 'tesseract',
        'tesseract_config': {
            'psm_mode': 7,
            'oem_mode': 1,
            'whitelist': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        },
        'deep_learning': {
            'input_width': 100,
            'input_height': 32
        },
        'preprocessing': {
            'enhance_contrast': True
        },
        'postprocessing': {
            'min_plate_length': 4,
            'max_plate_length': 10,
            'apply_regex_validation': False
        },
        'regional_settings': {
            'plate_format': r'^[A-Z]{3}\d{3}$'
        }
    }


@pytest.fixture
def camera_settings():
    """Camera detection settings."""
    return {
        'confidence_threshold': 0.8,
        'min_plate_size': 5
    }


@pytest.fixture
def mock_tensorflow_model():
    """Mock TensorFlow model for testing."""
    mock_model = Mock()
    # Mock output shape for CTC decoding
    mock_model.predict.return_value = np.random.rand(1, 20, 36)  # (batch, time, classes)
    return mock_model


@pytest.fixture
def mock_hailo_device():
    """Mock Hailo device for testing."""
    mock_device = Mock()
    mock_model = Mock()
    mock_output = Mock()
    mock_output.get_data.return_value = np.random.rand(1, 20, 36)
    mock_device.run.return_value = [mock_output]
    mock_device.load_model.return_value = mock_model
    return mock_device, mock_model


@pytest.fixture
def char_map():
    """Character mapping for OCR testing."""
    return {i: chr(65 + i) for i in range(26)} | {26 + i: str(i) for i in range(10)}


@pytest.fixture
def performance_config():
    """Performance configuration."""
    return {
        'enable_buffer_prealloc': True,
        'enable_parallel': True,
        'max_workers': 4,
        'frame_skip_threshold': 0.033,
        'enable_monitoring': True,
        'cache_metrics_enabled': True,
        'cache_health_check_interval': 60
    }


@pytest.fixture
def cache_config():
    """Cache configuration."""
    return {
        'enabled': True,
        'memory': {
            'max_size': 1000,
            'default_ttl': 300
        },
        'redis': {
            'enabled': False,
            'host': 'localhost',
            'port': 6379
        },
        'file': {
            'enabled': True,
            'cache_dir': 'cache/detector'
        }
    }


@pytest.fixture
def mock_thread_pool():
    """Mock thread pool executor."""
    mock_executor = Mock()
    mock_future = Mock()
    mock_future.result.return_value = "ABC123"
    mock_executor.submit.return_value = mock_future
    return mock_executor


@pytest.fixture
def large_frame():
    """Large frame for performance testing."""
    return np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)


@pytest.fixture
def multiple_plates_frame():
    """Frame with multiple potential license plates."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Add multiple rectangles of different sizes
    cv2.rectangle(frame, (100, 150), (300, 200), (255, 255, 255), -1)  # Valid size
    cv2.rectangle(frame, (400, 250), (500, 270), (255, 255, 255), -1)  # Smaller
    cv2.rectangle(frame, (50, 300), (600, 320), (255, 255, 255), -1)   # Too wide

    return frame


@pytest.fixture
def noisy_frame():
    """Frame with noise for testing robustness."""
    frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
    # Add some structured noise that might be detected as plates
    cv2.rectangle(frame, (200, 200), (400, 250), (200, 200, 200), -1)
    return frame


@pytest.fixture
def edge_case_frame():
    """Frame for edge case testing."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Very small potential plate
    cv2.rectangle(frame, (300, 220), (310, 230), (255, 255, 255), -1)
    # Plate at edge of frame
    cv2.rectangle(frame, (630, 230), (640, 240), (255, 255, 255), -1)
    return frame


@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing."""
    with pytest.mock.patch('os.path.exists') as mock_exists, \
         pytest.mock.patch('os.makedirs') as mock_makedirs, \
         pytest.mock.patch('builtins.open') as mock_open_file, \
         pytest.mock.patch('cv2.imwrite') as mock_imwrite:

        mock_exists.return_value = True
        mock_open_file.return_value.__enter__.return_value.read.return_value = '{"test": "data"}'
        yield {
            'exists': mock_exists,
            'makedirs': mock_makedirs,
            'open': mock_open_file,
            'imwrite': mock_imwrite
        }


@pytest.fixture
def mock_time():
    """Mock time operations."""
    with pytest.mock.patch('time.time') as mock_time_func, \
         pytest.mock.patch('time.perf_counter') as mock_perf_counter:

        mock_time_func.return_value = 1234567890.0
        mock_perf_counter.return_value = 1234567890.0
        yield {
            'time': mock_time_func,
            'perf_counter': mock_perf_counter
        }


@pytest.fixture
def mock_logging():
    """Mock logging for testing."""
    with pytest.mock.patch('logging.getLogger') as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


# Custom markers for test organization
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "ocr: OCR-specific tests")
    config.addinivalue_line("markers", "cache: Cache-specific tests")
    config.addinivalue_line("markers", "camera: Camera-specific tests")


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment for each test."""
    # Ensure clean test environment
    yield
    # Cleanup after test if needed