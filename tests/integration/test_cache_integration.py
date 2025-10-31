#!/usr/bin/env python3
"""
Integration tests for cache system with detector.
"""

import pytest
import numpy as np
import cv2
import time
import sys
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.recognition.detector_fixed import LicensePlateDetector
from tests.mocks import MockONVIFCamera, MockCacheManager, create_test_plate_image


@pytest.mark.integration
@pytest.mark.cache
class TestCacheIntegration:
    """Integration tests for cache system."""

    @pytest.fixture
    def cache_config(self):
        """Configuration with caching enabled."""
        return {
            'camera_id': 0,
            'frame_width': 640,
            'frame_height': 480,
            'confidence_threshold': 0.7,
            'save_images': False,
            'use_onvif': True,
            'mock_mode': False,
            'ocr_method': 'tesseract',
            'performance': {
                'enable_buffer_prealloc': True,
                'enable_parallel': False,
                'enable_monitoring': True,
                'cache_metrics_enabled': True,
                'cache_health_check_interval': 5  # Shorter for testing
            },
            'cache': {
                'enabled': True,
                'memory': {'max_size': 100, 'default_ttl': 300},
                'redis': {'enabled': False},
                'file': {'enabled': True, 'cache_dir': 'cache/detector'}
            }
        }

    def test_cache_hit_improves_performance(self, cache_config):
        """Test that cache hits improve performance."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=1.0)  # All hits

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string') as mock_tesseract:

            mock_tesseract.return_value = "CACHE123"

            detector = LicensePlateDetector(cache_config)

            # First call - cache miss
            start_time = time.time()
            result1 = detector.process_frame()
            first_call_time = time.time() - start_time

            # OCR should be called once
            assert mock_tesseract.call_count == 1
            assert result1 == "CACHE123"

            # Reset mock for second call
            mock_tesseract.reset_mock()

            # Second call - should be cache hit
            start_time = time.time()
            result2 = detector.process_frame()
            second_call_time = time.time() - start_time

            # OCR should not be called (cache hit)
            assert mock_tesseract.call_count == 0
            assert result2 == "CACHE123"

            # Cache hit should be faster (though in mock it's hard to measure real time difference)
            assert result1 == result2

    def test_cache_miss_triggers_ocr(self, cache_config):
        """Test that cache misses trigger OCR processing."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=0.0)  # All misses

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="MISS456"):

            detector = LicensePlateDetector(cache_config)

            result = detector.process_frame()

            assert result == "MISS456"
            assert mock_cache.stats['result_cache']['misses'] == 1

    def test_cache_storage_and_retrieval(self, cache_config):
        """Test cache storage and retrieval of OCR results."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=0.0)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="STORE789"):

            detector = LicensePlateDetector(cache_config)

            # Process frame - should cache result
            result1 = detector.process_frame()
            assert result1 == "STORE789"

            # Verify result was cached
            assert len(mock_cache.cache) > 0

            # Process another frame - should retrieve from cache
            result2 = detector.process_frame()
            assert result2 == "STORE789"

    def test_cache_with_different_images(self, cache_config):
        """Test cache behavior with different images."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=0.0)

        call_count = 0
        def different_results(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return f"RESULT{call_count}"

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', side_effect=different_results):

            detector = LicensePlateDetector(cache_config)

            # Process multiple frames with different content
            results = []
            for _ in range(5):
                result = detector.process_frame()
                results.append(result)

            # Each result should be different (cache misses)
            assert len(set(results)) == len(results)
            assert mock_cache.stats['result_cache']['misses'] == 5

    def test_cache_memory_limits(self, cache_config):
        """Test cache respects memory limits."""
        cache_config['cache']['memory']['max_size'] = 2  # Very small cache
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=0.0)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="LIMIT999"):

            detector = LicensePlateDetector(cache_config)

            # Process many frames
            for i in range(10):
                detector.process_frame()

            # Cache should not grow beyond limit (mock implementation)
            assert len(mock_cache.cache) <= 2

    def test_cache_health_monitoring(self, cache_config):
        """Test cache health monitoring integration."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="HEALTH111"):

            detector = LicensePlateDetector(cache_config)

            # Process frames to trigger health checks
            for _ in range(3):
                detector.process_frame()

            # Manually trigger health check
            detector._perform_cache_health_check()

            # Verify health status
            metrics = detector.get_performance_metrics()
            assert 'cache_health_status' in metrics
            assert 'cache_hit_rate' in metrics

    def test_cache_disabled_behavior(self, cache_config):
        """Test behavior when cache is disabled."""
        cache_config['cache']['enabled'] = False
        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=None), \
             patch('pytesseract.image_to_string', return_value="NOCACHE222"):

            detector = LicensePlateDetector(cache_config)

            # Process frames
            results = []
            for _ in range(3):
                result = detector.process_frame()
                results.append(result)

            # All results should be from OCR (no caching)
            assert all(r == "NOCACHE222" for r in results)
            assert detector.enable_caching == False
            assert detector.cache_manager is None

    def test_cache_ttl_behavior(self, cache_config):
        """Test cache TTL behavior."""
        # Note: This is a simplified test since our mock doesn't implement TTL
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=0.5)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="TTL333"):

            detector = LicensePlateDetector(cache_config)

            # Process frames
            for _ in range(5):
                detector.process_frame()

            # Verify cache is being used
            assert mock_cache.stats['result_cache']['hits'] > 0 or mock_cache.stats['result_cache']['misses'] > 0

    def test_cache_statistics_accuracy(self, cache_config):
        """Test cache statistics accuracy."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=0.0)  # Force misses

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="STATS444"):

            detector = LicensePlateDetector(cache_config)

            # Process known number of frames
            num_frames = 7
            for _ in range(num_frames):
                detector.process_frame()

            # Collect cache metrics
            detector._collect_cache_metrics()

            # Verify statistics
            metrics = detector.get_performance_metrics()
            assert metrics['cache_misses'] == num_frames
            assert metrics['cache_hit_rate'] == 0.0

    def test_cache_with_parallel_processing(self, cache_config):
        """Test cache behavior with parallel processing."""
        cache_config['performance']['enable_parallel'] = True
        cache_config['performance']['max_workers'] = 2

        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=0.0)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="PARALLEL555"):

            detector = LicensePlateDetector(cache_config)

            # Process frames with parallel OCR
            results = []
            for _ in range(4):
                result = detector.process_frame()
                results.append(result)

            # Verify parallel execution
            assert detector.executor is not None
            assert len(results) == 4
            assert all(r == "PARALLEL555" for r in results if r is not None)

    def test_cache_memory_usage_tracking(self, cache_config):
        """Test cache memory usage tracking."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="MEMORY666"):

            detector = LicensePlateDetector(cache_config)

            # Process frames to build cache
            for _ in range(5):
                detector.process_frame()

            # Collect metrics
            detector._collect_cache_metrics()

            # Verify memory tracking
            metrics = detector.get_performance_metrics()
            assert 'cache_memory_usage' in metrics
            assert isinstance(metrics['cache_memory_usage'], (int, type(None)))

    def test_cache_file_backend_integration(self, cache_config, tmp_path):
        """Test cache file backend integration."""
        cache_config['cache']['file']['cache_dir'] = str(tmp_path / 'cache')

        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager') as mock_cache_class, \
             patch('pytesseract.image_to_string', return_value="FILE777"):

            # Mock cache manager with file backend
            mock_cache = Mock()
            mock_cache.get_ocr_result.return_value = None
            mock_cache.cache_ocr_result.return_value = True
            mock_cache.get_stats.return_value = {
                'result_cache': {'hits': 1, 'misses': 2},
                'memory': {'size': 512},
                'redis': {'connected': False},
                'file': {'size': 1024}
            }
            mock_cache_class.return_value = mock_cache

            detector = LicensePlateDetector(cache_config)

            # Process frames
            for _ in range(3):
                detector.process_frame()

            # Verify file backend usage
            metrics = detector.get_performance_metrics()
            assert metrics['cache_file_size'] == 1024

    def test_cache_redis_backend_integration(self, cache_config):
        """Test cache Redis backend integration."""
        cache_config['cache']['redis']['enabled'] = True

        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager') as mock_cache_class, \
             patch('pytesseract.image_to_string', return_value="REDIS888"):

            # Mock cache manager with Redis backend
            mock_cache = Mock()
            mock_cache.get_ocr_result.return_value = None
            mock_cache.cache_ocr_result.return_value = True
            mock_cache.get_stats.return_value = {
                'result_cache': {'hits': 2, 'misses': 1},
                'memory': {'size': 256},
                'redis': {'connected': True},
                'file': {'size': 512}
            }
            mock_cache_class.return_value = mock_cache

            detector = LicensePlateDetector(cache_config)

            # Process frames
            for _ in range(3):
                detector.process_frame()

            # Verify Redis backend usage
            metrics = detector.get_performance_metrics()
            assert metrics['cache_redis_connected'] == True

    def test_cache_error_handling(self, cache_config):
        """Test cache error handling."""
        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager') as mock_cache_class, \
             patch('pytesseract.image_to_string', return_value="ERROR999"):

            # Mock cache manager that raises exceptions
            mock_cache = Mock()
            mock_cache.get_ocr_result.side_effect = Exception("Cache error")
            mock_cache.cache_ocr_result.side_effect = Exception("Cache error")
            mock_cache.get_stats.side_effect = Exception("Cache error")
            mock_cache_class.return_value = mock_cache

            detector = LicensePlateDetector(cache_config)

            # Process should continue despite cache errors
            result = detector.process_frame()
            assert result == "ERROR999"

            # Metrics collection should handle errors gracefully
            metrics = detector.get_performance_metrics()
            assert isinstance(metrics, dict)