#!/usr/bin/env python3
"""
Integration tests for LicensePlateDetector with real component interactions.
"""

import pytest
import numpy as np
import cv2
import tempfile
import os
import sys
import time
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.recognition.detector_fixed import LicensePlateDetector
from tests.mocks import MockONVIFCamera, MockCacheManager, create_test_plate_image


@pytest.mark.integration
class TestDetectorIntegration:
    """Integration tests for detector with multiple components."""

    @pytest.fixture
    def integration_config(self):
        """Configuration for integration testing."""
        return {
            'camera_id': 0,
            'frame_width': 640,
            'frame_height': 480,
            'confidence_threshold': 0.7,
            'save_images': False,
            'image_save_path': 'data/images',
            'use_onvif': True,
            'mock_mode': False,
            'ocr_method': 'tesseract',
            'performance': {
                'enable_buffer_prealloc': True,
                'enable_parallel': True,
                'max_workers': 2,
                'enable_monitoring': True
            },
            'cache': {
                'enabled': True,
                'memory': {'max_size': 100, 'default_ttl': 300},
                'redis': {'enabled': False},
                'file': {'enabled': True, 'cache_dir': 'cache/detector'}
            }
        }

    def test_detector_with_mock_camera_and_cache(self, integration_config):
        """Test detector integration with mock camera and cache."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=0.0)  # No cache hits initially

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="ABC123"):

            detector = LicensePlateDetector(integration_config)

            # Process multiple frames
            results = []
            for _ in range(5):
                result = detector.process_frame()
                results.append(result)

            # Verify results
            assert len(results) == 5
            # Some frames should have plates detected
            plate_results = [r for r in results if r is not None]
            assert len(plate_results) > 0

            # Verify cache interactions
            assert mock_cache.stats['result_cache']['misses'] > 0

    def test_detector_with_cache_hits(self, integration_config):
        """Test detector with cache hits."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=1.0)  # All cache hits

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="XYZ789"):

            detector = LicensePlateDetector(integration_config)

            # Process frames
            results = []
            for _ in range(3):
                result = detector.process_frame()
                results.append(result)

            # Verify cache hits
            assert mock_cache.stats['result_cache']['hits'] > 0

    def test_detector_performance_monitoring(self, integration_config):
        """Test performance monitoring across multiple frames."""
        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=MockCacheManager(enabled=False)), \
             patch('pytesseract.image_to_string', return_value="TEST123"):

            detector = LicensePlateDetector(integration_config)

            # Process multiple frames
            start_time = time.time()
            for _ in range(10):
                detector.process_frame()
            end_time = time.time()

            # Verify performance metrics
            metrics = detector.get_performance_metrics()
            assert metrics['frame_count'] == 10
            assert metrics['total_time'] > 0
            assert 'avg_latency' in metrics
            assert len(metrics['processing_times']) <= 100  # Capped at 100

    def test_detector_with_image_saving(self, integration_config, tmp_path):
        """Test detector with image saving enabled."""
        integration_config['save_images'] = True
        integration_config['image_save_path'] = str(tmp_path / 'images')

        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=MockCacheManager(enabled=False)), \
             patch('pytesseract.image_to_string', return_value="SAVE123"), \
             patch('cv2.imwrite') as mock_imwrite:

            detector = LicensePlateDetector(integration_config)

            result = detector.process_frame()

            # Verify image saving was attempted
            assert result == "SAVE123"
            mock_imwrite.assert_called()

    def test_detector_error_recovery(self, integration_config):
        """Test detector error recovery mechanisms."""
        mock_camera = MockONVIFCamera()

        # Simulate OCR failures
        call_count = 0
        def failing_ocr(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("OCR temporarily failed")
            return "RECOVER123"

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=MockCacheManager(enabled=False)), \
             patch('pytesseract.image_to_string', side_effect=failing_ocr):

            detector = LicensePlateDetector(integration_config)

            # Process frames - should eventually recover
            results = []
            for _ in range(5):
                result = detector.process_frame()
                results.append(result)

            # Should have some successful results after recovery
            successful_results = [r for r in results if r is not None]
            assert len(successful_results) > 0

    def test_detector_with_different_ocr_methods(self, integration_config):
        """Test detector with different OCR methods."""
        mock_camera = MockONVIFCamera()

        # Test Tesseract
        integration_config['ocr_method'] = 'tesseract'
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=MockCacheManager(enabled=False)), \
             patch('pytesseract.image_to_string', return_value="TESS123"):

            detector = LicensePlateDetector(integration_config)
            result = detector.process_frame()
            assert result == "TESS123"

        # Test deep learning (mocked)
        integration_config['ocr_method'] = 'deep_learning'
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=MockCacheManager(enabled=False)), \
             patch('src.recognition.detector_fixed.TENSORFLOW_AVAILABLE', True), \
             patch.object(LicensePlateDetector, '_deep_learning_ocr', return_value="DL456"):

            detector = LicensePlateDetector(integration_config)
            result = detector.process_frame()
            assert result == "DL456"

    def test_detector_parallel_processing_integration(self, integration_config):
        """Test detector with parallel processing enabled."""
        integration_config['performance']['enable_parallel'] = True
        integration_config['performance']['max_workers'] = 4

        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=MockCacheManager(enabled=False)), \
             patch('pytesseract.image_to_string', return_value="PARALLEL789"):

            detector = LicensePlateDetector(integration_config)

            # Verify thread pool is created
            assert detector.executor is not None
            assert detector.enable_parallel == True

            # Process frames
            results = []
            for _ in range(3):
                result = detector.process_frame()
                results.append(result)

            # Verify results
            assert all(r == "PARALLEL789" for r in results if r is not None)

    def test_detector_cache_health_monitoring(self, integration_config):
        """Test cache health monitoring integration."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="HEALTH123"):

            detector = LicensePlateDetector(integration_config)

            # Process frames to trigger health checks
            for _ in range(5):
                detector.process_frame()

            # Manually trigger health check
            detector._perform_cache_health_check()

            # Verify health status is tracked
            metrics = detector.get_performance_metrics()
            assert 'cache_health_status' in metrics

    def test_detector_memory_management(self, integration_config):
        """Test detector memory management with buffer pools."""
        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=MockCacheManager(enabled=False)), \
             patch('pytesseract.image_to_string', return_value="MEMORY123"):

            detector = LicensePlateDetector(integration_config)

            # Verify buffer preallocation
            assert hasattr(detector, 'frame_buffer')
            assert hasattr(detector, 'gray_buffer')
            assert hasattr(detector, 'plate_pool')

            # Process frames to test memory pool usage
            for _ in range(15):  # More than pool size (10)
                detector.process_frame()

            # Verify memory pool is utilized
            assert detector.plate_pool.qsize() <= 10  # Pool size limit

    def test_detector_configuration_persistence(self, integration_config, tmp_path):
        """Test detector configuration loading and reloading."""
        config_file = tmp_path / 'ocr_config.json'
        ocr_config = {
            'ocr_method': 'tesseract',
            'tesseract_config': {'psm_mode': 8},
            'preprocessing': {'enhance_contrast': True}
        }

        # Write config to file
        import json
        config_file.write_text(json.dumps(ocr_config))

        integration_config['ocr_config_path'] = str(config_file)
        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=MockCacheManager(enabled=False)), \
             patch('pytesseract.image_to_string', return_value="CONFIG123"):

            detector = LicensePlateDetector(integration_config)

            # Verify config was loaded
            assert detector.ocr_method == 'tesseract'
            assert detector.tesseract_config['psm_mode'] == 8

            # Test config reload
            new_config = ocr_config.copy()
            new_config['ocr_method'] = 'deep_learning'

            success = detector.reload_ocr_config(new_config)
            assert success == True
            assert detector.ocr_method == 'deep_learning'

    def test_detector_frame_skip_logic(self, integration_config):
        """Test frame skipping logic under high frame rates."""
        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=MockCacheManager(enabled=False)), \
             patch('pytesseract.image_to_string', return_value="SKIP123"):

            detector = LicensePlateDetector(integration_config)

            # Simulate high frame rate by setting last process time
            detector.last_process_time = time.perf_counter() - 0.01  # Within skip threshold

            result = detector.process_frame()

            # Frame should be skipped
            assert result is None

            # Verify skip was recorded in metrics
            metrics = detector.get_performance_metrics()
            assert metrics['skipped_frames'] >= 1

    def test_detector_cleanup_integration(self, integration_config):
        """Test detector cleanup with all components."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="CLEANUP123"):

            detector = LicensePlateDetector(integration_config)

            # Process some frames to generate metrics
            for _ in range(3):
                detector.process_frame()

            # Perform cleanup
            detector.cleanup()

            # Verify cleanup actions
            metrics = detector.get_performance_metrics()
            assert 'cache_hits' in metrics
            assert 'cache_misses' in metrics

    def test_detector_with_real_image_processing(self, integration_config):
        """Test detector with real OpenCV image processing."""
        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=MockCacheManager(enabled=False)), \
             patch('pytesseract.image_to_string', return_value="REALIMG456"):

            detector = LicensePlateDetector(integration_config)

            # Process frames
            results = []
            for _ in range(5):
                result = detector.process_frame()
                results.append(result)

            # Verify OpenCV operations work correctly
            successful_results = [r for r in results if r is not None]
            assert len(successful_results) > 0

            # Verify frame processing metrics
            metrics = detector.get_performance_metrics()
            assert metrics['frame_count'] == 5

    def test_detector_stress_test(self, integration_config):
        """Stress test detector with many frames."""
        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=MockCacheManager(enabled=False)), \
             patch('pytesseract.image_to_string', return_value="STRESS789"):

            detector = LicensePlateDetector(integration_config)

            # Process many frames
            num_frames = 50
            results = []
            start_time = time.time()

            for _ in range(num_frames):
                result = detector.process_frame()
                results.append(result)

            end_time = time.time()
            processing_time = end_time - start_time

            # Verify performance
            metrics = detector.get_performance_metrics()
            assert metrics['frame_count'] == num_frames
            assert processing_time < 30  # Should complete within reasonable time

            # Verify memory stability (no memory leaks)
            assert detector.plate_pool.qsize() <= 10  # Pool size limit maintained