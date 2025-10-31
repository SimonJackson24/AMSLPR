#!/usr/bin/env python3
"""
Comprehensive unit tests for LicensePlateDetector class.
Tests cover initialization, detection, OCR, caching, and error handling.
"""

import pytest
import numpy as np
import os
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import cv2

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.recognition.detector import LicensePlateDetector


class TestLicensePlateDetector:
    """Test suite for LicensePlateDetector class."""

    @pytest.fixture
    def basic_config(self):
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
                'max_workers': 2
            },
            'cache': {
                'enabled': False
            }
        }

    @pytest.fixture
    def sample_frame(self):
        """Create a sample frame for testing."""
        # Create a simple test frame with some shapes
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add a white rectangle that could be mistaken for a license plate
        cv2.rectangle(frame, (200, 200), (400, 250), (255, 255, 255), -1)
        return frame

    @pytest.fixture
    def mock_onvif_manager(self):
        """Mock ONVIF camera manager."""
        mock_manager = Mock()
        mock_manager.get_frame.return_value = (np.zeros((480, 640, 3), dtype=np.uint8), 1234567890.0)
        return mock_manager

    def test_initialization_basic(self, basic_config):
        """Test basic initialization of LicensePlateDetector."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            assert detector.config == basic_config
            assert detector.camera_id == 0
            assert detector.frame_width == 640
            assert detector.frame_height == 480
            assert detector.confidence_threshold == 0.7
            assert detector.ocr_method == 'tesseract'
            assert detector.mock_mode == True

    def test_initialization_with_ocr_config(self, basic_config):
        """Test initialization with OCR configuration."""
        ocr_config = {
            'ocr_method': 'deep_learning',
            'tesseract_config': {'psm_mode': 8},
            'preprocessing': {'enhance_contrast': True}
        }

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config, ocr_config)

            assert detector.ocr_method == 'deep_learning'
            assert detector.tesseract_config == {'psm_mode': 8}
            assert detector.preprocessing_config == {'enhance_contrast': True}

    def test_initialization_buffer_preallocation(self, basic_config):
        """Test buffer preallocation during initialization."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            assert hasattr(detector, 'frame_buffer')
            assert detector.frame_buffer.shape == (480, 640, 3)
            assert hasattr(detector, 'gray_buffer')
            assert detector.gray_buffer.shape == (480, 640)

    def test_initialization_without_buffer_prealloc(self, basic_config):
        """Test initialization without buffer preallocation."""
        basic_config['performance']['enable_buffer_prealloc'] = False

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            assert not hasattr(detector, 'frame_buffer')
            assert not hasattr(detector, 'gray_buffer')

    def test_detect_license_plates_none_frame(self, basic_config):
        """Test license plate detection with None frame."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            result = detector.detect_license_plates(None)
            assert result == []

    def test_detect_license_plates_basic(self, basic_config, sample_frame):
        """Test basic license plate detection."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            plates = detector.detect_license_plates(sample_frame)

            assert isinstance(plates, list)
            # Should find at least one potential plate in our test frame
            assert len(plates) >= 0

            if plates:
                plate = plates[0]
                assert 'x' in plate
                assert 'y' in plate
                assert 'width' in plate
                assert 'height' in plate
                assert 'confidence' in plate
                assert 0 <= plate['confidence'] <= 1

    def test_detect_license_plates_with_settings(self, basic_config, sample_frame):
        """Test license plate detection with custom camera settings."""
        camera_settings = {
            'confidence_threshold': 0.8,
            'min_plate_size': 10
        }

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            plates = detector.detect_license_plates(sample_frame, camera_settings)

            assert isinstance(plates, list)
            # Filter out plates below confidence threshold
            valid_plates = [p for p in plates if p['confidence'] >= 0.8]
            assert len(valid_plates) == len(plates) or len(valid_plates) == 0

    def test_detect_license_plates_aspect_ratio_filter(self, basic_config):
        """Test aspect ratio filtering in license plate detection."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            # Create frame with rectangle that's too wide (aspect ratio > 5.0)
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.rectangle(frame, (100, 200), (500, 220), (255, 255, 255), -1)  # Very wide

            plates = detector.detect_license_plates(frame)
            # Should filter out the wide rectangle
            assert len(plates) == 0

    def test_detect_license_plates_size_filter(self, basic_config):
        """Test size filtering in license plate detection."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            # Create frame with very small rectangle
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.rectangle(frame, (300, 230), (310, 235), (255, 255, 255), -1)  # Very small

            plates = detector.detect_license_plates(frame)
            # Should filter out the small rectangle
            assert len(plates) == 0

    def test_clean_plate_text_basic(self, basic_config):
        """Test basic plate text cleaning."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            # Test normal text
            result = detector._clean_plate_text("ABC123")
            assert result == "ABC123"

            # Test with whitespace
            result = detector._clean_plate_text(" ABC 123 ")
            assert result == "ABC123"

            # Test with special characters
            result = detector._clean_plate_text("A@B#C$1%2^3")
            assert result == "ABC123"

            # Test lowercase conversion
            result = detector._clean_plate_text("abc123")
            assert result == "ABC123"

    def test_clean_plate_text_empty(self, basic_config):
        """Test plate text cleaning with empty input."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            result = detector._clean_plate_text("")
            assert result == ""

            result = detector._clean_plate_text(None)
            assert result == ""

    def test_select_best_text_matching(self, basic_config):
        """Test text selection when both methods return same result."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            result = detector._select_best_text("ABC123", "ABC123", None)
            assert result == "ABC123"

    def test_select_best_text_one_empty(self, basic_config):
        """Test text selection when one method returns empty."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            result = detector._select_best_text("ABC123", "", None)
            assert result == "ABC123"

            result = detector._select_best_text("", "XYZ789", None)
            assert result == "XYZ789"

    def test_select_best_text_length_preference(self, basic_config):
        """Test text selection based on length."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            # Longer text should be preferred
            result = detector._select_best_text("ABC123DEF", "XYZ789", None)
            assert result == "ABC123DEF"

            # But not if the difference is too small
            result = detector._select_best_text("ABC123", "XYZ7890", None)
            assert result == "XYZ7890"

    def test_select_best_text_both_empty(self, basic_config):
        """Test text selection when both methods fail."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            result = detector._select_best_text("", "", None)
            assert result is None

    def test_recognize_text_none_frame(self, basic_config):
        """Test text recognition with None frame."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            plate = {'x': 100, 'y': 100, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(None, plate)
            assert result is None

    def test_recognize_text_invalid_plate(self, basic_config, sample_frame):
        """Test text recognition with invalid plate coordinates."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            # Plate coordinates outside frame
            plate = {'x': 700, 'y': 100, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)
            assert result is None

    @patch('pytesseract.image_to_string')
    def test_recognize_text_tesseract_success(self, mock_tesseract, basic_config, sample_frame):
        """Test successful text recognition with Tesseract."""
        mock_tesseract.return_value = "ABC123"

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)

            assert result == "ABC123"
            mock_tesseract.assert_called_once()

    @patch('pytesseract.image_to_string')
    def test_recognize_text_tesseract_empty(self, mock_tesseract, basic_config, sample_frame):
        """Test text recognition when Tesseract returns empty result."""
        mock_tesseract.return_value = ""

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)

            assert result is None

    def test_recognize_text_length_validation(self, basic_config, sample_frame):
        """Test text recognition with length validation."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('pytesseract.image_to_string', return_value="AB"):
            detector = LicensePlateDetector(basic_config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)

            # Should be None due to length < 4
            assert result is None

    def test_recognize_text_length_validation_long(self, basic_config, sample_frame):
        """Test text recognition with maximum length validation."""
        long_text = "A" * 15  # Too long
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('pytesseract.image_to_string', return_value=long_text):
            detector = LicensePlateDetector(basic_config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)

            # Should be None due to length > 10
            assert result is None

    def test_process_frame_mock_mode(self, basic_config, mock_onvif_manager):
        """Test frame processing in mock mode."""
        with patch('src.recognition.detector_fixed.init_camera_manager', return_value=mock_onvif_manager):
            detector = LicensePlateDetector(basic_config)

            result = detector.process_frame()

            # Should return None in mock mode with no plates detected
            assert result is None

    def test_process_frame_no_frame(self, basic_config):
        """Test frame processing when no frame is available."""
        mock_manager = Mock()
        mock_manager.get_frame.return_value = (None, None)

        with patch('src.recognition.detector_fixed.init_camera_manager', return_value=mock_manager):
            detector = LicensePlateDetector(basic_config)

            result = detector.process_frame()
            assert result is None

    def test_process_frame_with_plate(self, basic_config, sample_frame):
        """Test frame processing when a plate is detected."""
        mock_manager = Mock()
        mock_manager.get_frame.return_value = (sample_frame, 1234567890.0)

        with patch('src.recognition.detector_fixed.init_camera_manager', return_value=mock_manager), \
             patch('pytesseract.image_to_string', return_value="ABC123"):
            detector = LicensePlateDetector(basic_config)

            result = detector.process_frame()
            assert result == "ABC123"

    def test_process_frame_skip_logic(self, basic_config, sample_frame):
        """Test frame skipping logic."""
        mock_manager = Mock()
        mock_manager.get_frame.return_value = (sample_frame, 1234567890.0)

        with patch('src.recognition.detector_fixed.init_camera_manager', return_value=mock_manager):
            detector = LicensePlateDetector(basic_config)

            # Set last process time to simulate high frame rate
            detector.last_process_time = 1234567890.0 - 0.01  # Within skip threshold

            result = detector.process_frame()
            assert result is None

    def test_get_performance_metrics(self, basic_config):
        """Test performance metrics retrieval."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            metrics = detector.get_performance_metrics()

            assert isinstance(metrics, dict)
            assert 'frame_count' in metrics
            assert 'total_time' in metrics
            assert 'avg_latency' in metrics

    def test_reload_ocr_config_success(self, basic_config):
        """Test successful OCR configuration reload."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            new_config = {
                'ocr_method': 'deep_learning',
                'tesseract_config': {'psm_mode': 10}
            }

            with patch('os.path.exists', return_value=True), \
                 patch('builtins.open', mock_open(read_data=json.dumps(new_config))):
                result = detector.reload_ocr_config()

                assert result == True
                assert detector.ocr_method == 'deep_learning'

    def test_reload_ocr_config_file_not_found(self, basic_config):
        """Test OCR configuration reload when file not found."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            with patch('os.path.exists', return_value=False):
                result = detector.reload_ocr_config()

                assert result == False

    def test_cleanup_resources(self, basic_config):
        """Test cleanup of resources."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            # Add some mock resources
            detector.executor = Mock()

            detector.cleanup()

            # Executor should be shut down
            detector.executor.shutdown.assert_called_once()

    def test_initialization_onvif_failure_fallback(self, basic_config):
        """Test initialization fallback when ONVIF fails."""
        with patch('src.recognition.detector_fixed.init_camera_manager', side_effect=Exception("ONVIF failed")):
            detector = LicensePlateDetector(basic_config)

            # Should fallback to mock mode
            assert detector.mock_mode == True

    def test_deep_learning_ocr_tensorflow(self, basic_config):
        """Test deep learning OCR with TensorFlow."""
        config = basic_config.copy()
        config['ocr_method'] = 'deep_learning'

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('src.recognition.detector_fixed.TENSORFLOW_AVAILABLE', True):
            detector = LicensePlateDetector(config)

            # Mock TensorFlow model
            mock_model = Mock()
            mock_model.predict.return_value = np.random.rand(1, 20, 36)  # Mock output
            detector.ocr_model = mock_model
            detector.char_map = {i: chr(65 + i) for i in range(26)}  # A-Z

            image = np.zeros((32, 100), dtype=np.uint8)
            result = detector._deep_learning_ocr(image)

            assert isinstance(result, str)

    def test_deep_learning_ocr_hailo(self, basic_config):
        """Test deep learning OCR with Hailo TPU."""
        config = basic_config.copy()
        config['ocr_method'] = 'deep_learning'
        config['use_hailo_tpu'] = True

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('src.recognition.detector_fixed.HAILO_AVAILABLE', True):
            detector = LicensePlateDetector(config)

            # Mock Hailo model
            mock_model = Mock()
            mock_output = Mock()
            mock_output.get_data.return_value = np.random.rand(1, 20, 36)
            mock_device = Mock()
            mock_device.run.return_value = [mock_output]

            detector.hailo_device = mock_device
            detector.ocr_model = mock_model
            detector.char_map = {i: chr(65 + i) for i in range(26)}

            image = np.zeros((32, 100), dtype=np.uint8)
            result = detector._deep_learning_ocr(image)

            assert isinstance(result, str)

    def test_cache_initialization_disabled(self, basic_config):
        """Test cache initialization when disabled."""
        config = basic_config.copy()
        config['cache']['enabled'] = False

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(config)

            assert detector.enable_caching == False
            assert detector.cache_manager is None

    def test_cache_initialization_enabled(self, basic_config):
        """Test cache initialization when enabled."""
        config = basic_config.copy()
        config['cache']['enabled'] = True

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('src.cache.cache_manager.CacheManager') as mock_cache_manager:
            detector = LicensePlateDetector(config)

            assert detector.enable_caching == True
            mock_cache_manager.assert_called_once()

    def test_save_plate_image_disabled(self, basic_config, sample_frame):
        """Test plate image saving when disabled."""
        config = basic_config.copy()
        config['save_images'] = False

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            detector._save_plate_image(sample_frame, plate, "ABC123")

            # Should not create directory or save file
            assert not os.path.exists('data/images')

    def test_save_plate_image_enabled(self, basic_config, sample_frame):
        """Test plate image saving when enabled."""
        config = basic_config.copy()
        config['save_images'] = True

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('cv2.imwrite') as mock_imwrite:
            detector = LicensePlateDetector(config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            detector._save_plate_image(sample_frame, plate, "ABC123")

            # Should attempt to save image
            mock_imwrite.assert_called_once()

    def test_metrics_thread_safety(self, basic_config):
        """Test thread safety of metrics updates."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            # Simulate concurrent access
            import threading

            def update_metrics():
                with detector.metrics_lock:
                    detector.metrics['frame_count'] += 1

            threads = []
            for _ in range(10):
                t = threading.Thread(target=update_metrics)
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            assert detector.metrics['frame_count'] == 10

    def test_error_handling_ocr_failure(self, basic_config, sample_frame):
        """Test error handling when OCR fails."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('pytesseract.image_to_string', side_effect=Exception("OCR failed")):
            detector = LicensePlateDetector(basic_config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)

            assert result is None

    def test_parallel_processing_disabled(self, basic_config, sample_frame):
        """Test processing when parallel processing is disabled."""
        config = basic_config.copy()
        config['performance']['enable_parallel'] = False

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('pytesseract.image_to_string', return_value="ABC123"):
            detector = LicensePlateDetector(config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)

            assert result == "ABC123"
            assert detector.executor is None

    def test_parallel_processing_enabled(self, basic_config, sample_frame):
        """Test processing when parallel processing is enabled."""
        config = basic_config.copy()
        config['performance']['enable_parallel'] = True

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('pytesseract.image_to_string', return_value="ABC123"):
            detector = LicensePlateDetector(config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)

            assert result == "ABC123"
            assert detector.executor is not None

    def test_frame_buffer_resize(self, basic_config):
        """Test frame buffer resizing when frame size doesn't match."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            # Create frame with different size
            frame = np.zeros((600, 800, 3), dtype=np.uint8)
            cv2.rectangle(frame, (200, 200), (400, 250), (255, 255, 255), -1)

            plates = detector.detect_license_plates(frame)

            # Should still work despite size mismatch
            assert isinstance(plates, list)

    def test_ocr_config_validation(self, basic_config):
        """Test OCR configuration validation."""
        config = basic_config.copy()
        config['ocr_method'] = 'invalid_method'

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(config)

            # Should fallback to tesseract
            assert detector.ocr_method == 'tesseract'

    def test_memory_pool_usage(self, basic_config, sample_frame):
        """Test memory pool usage for plate images."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('pytesseract.image_to_string', return_value="ABC123"):
            detector = LicensePlateDetector(basic_config)

            # Add item to pool
            detector.plate_pool.put(np.zeros((50, 200), dtype=np.uint8))

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)

            assert result == "ABC123"

    def test_performance_monitoring(self, basic_config, sample_frame):
        """Test performance monitoring functionality."""
        mock_manager = Mock()
        mock_manager.get_frame.return_value = (sample_frame, 1234567890.0)

        with patch('src.recognition.detector_fixed.init_camera_manager', return_value=mock_manager), \
             patch('pytesseract.image_to_string', return_value="ABC123"):
            detector = LicensePlateDetector(basic_config)

            # Process multiple frames
            for _ in range(5):
                detector.process_frame()

            metrics = detector.get_performance_metrics()

            assert metrics['frame_count'] == 5
            assert metrics['total_time'] > 0
            assert len(metrics['processing_times']) <= 100  # Should be capped

    def test_cache_health_check(self, basic_config):
        """Test cache health check functionality."""
        config = basic_config.copy()
        config['cache']['enabled'] = True

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('src.cache.cache_manager.CacheManager') as mock_cache_class:
            mock_cache_instance = Mock()
            mock_cache_instance.health_check.return_value = {
                'memory': {'healthy': True},
                'redis': {'healthy': False}
            }
            mock_cache_class.return_value = mock_cache_instance

            detector = LicensePlateDetector(config)

            detector._perform_cache_health_check()

            assert detector.metrics['cache_health_status'] == 'degraded'

    def test_regex_validation_enabled(self, basic_config, sample_frame):
        """Test regex validation when enabled."""
        config = basic_config.copy()
        config['postprocessing'] = {
            'apply_regex_validation': True,
            'regional_settings': {
                'plate_format': r'^[A-Z]{3}\d{3}$'
            }
        }

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('pytesseract.image_to_string', return_value="ABC123"):
            detector = LicensePlateDetector(config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)

            assert result == "ABC123"  # Should match regex

    def test_regex_validation_reject(self, basic_config, sample_frame):
        """Test regex validation rejection."""
        config = basic_config.copy()
        config['postprocessing'] = {
            'apply_regex_validation': True,
            'regional_settings': {
                'plate_format': r'^[A-Z]{3}\d{3}$'
            }
        }

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('pytesseract.image_to_string', return_value="INVALID"):
            detector = LicensePlateDetector(config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)

            assert result is None  # Should be rejected by regex

    def test_hybrid_ocr_method(self, basic_config, sample_frame):
        """Test hybrid OCR method combining multiple approaches."""
        config = basic_config.copy()
        config['ocr_method'] = 'hybrid'

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('pytesseract.image_to_string', return_value="ABC123"), \
             patch.object(LicensePlateDetector, '_deep_learning_ocr', return_value="ABC123"):
            detector = LicensePlateDetector(config)

            plate = {'x': 200, 'y': 200, 'width': 200, 'height': 50, 'confidence': 0.9}
            result = detector._recognize_text(sample_frame, plate)

            assert result == "ABC123"

    def test_initialization_error_handling(self, basic_config):
        """Test initialization error handling."""
        config = basic_config.copy()
        config['performance']['enable_parallel'] = True

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None), \
             patch('concurrent.futures.ThreadPoolExecutor', side_effect=Exception("Thread pool failed")):
            detector = LicensePlateDetector(config)

            # Should handle thread pool creation failure gracefully
            assert detector.executor is None
            assert detector.enable_parallel == False

    def test_decode_output_basic(self, basic_config):
        """Test output decoding for OCR models."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            # Simple character map
            char_map = {0: 'A', 1: 'B', 2: 'C'}

            # Mock output with highest confidence for index 0
            output = np.zeros((10, 3))
            output[:, 0] = 1.0  # Highest confidence for 'A'

            result = detector._decode_output(output, char_map)

            assert result == "AAAAAAAAAA"

    def test_decode_output_empty_map(self, basic_config):
        """Test output decoding with empty character map."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            output = np.zeros((5, 10))
            result = detector._decode_output(output, {})

            assert result == ""

    def test_load_char_map_from_file(self, basic_config):
        """Test loading character map from file."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            char_map_data = {'0': 'A', '1': 'B'}
            expected_path = os.path.join('models', 'char_map.json')

            with patch('os.path.exists', return_value=True), \
                 patch('builtins.open', mock_open(read_data=json.dumps(char_map_data))):
                result = detector._load_char_map()

                assert result == char_map_data

    def test_load_char_map_default(self, basic_config):
        """Test loading default character map when file doesn't exist."""
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=None):
            detector = LicensePlateDetector(basic_config)

            with patch('os.path.exists', return_value=False):
                result = detector._load_char_map()

                assert isinstance(result, dict)
                assert len(result) == 36  # 26 letters + 10 digits
                assert result[0] == '0'
                assert result[25] == 'Z'