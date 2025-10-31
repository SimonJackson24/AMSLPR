#!/usr/bin/env python3
"""
Performance regression tests for LicensePlateDetector.
Uses pytest-benchmark for automated performance monitoring.
"""

import pytest
import numpy as np
import cv2
import time
import sys
import psutil
import os
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.recognition.detector_fixed import LicensePlateDetector
from tests.mocks import MockONVIFCamera, MockCacheManager, create_performance_test_data


@pytest.mark.performance
class TestPerformanceRegression:
    """Performance regression tests using pytest-benchmark."""

    @pytest.fixture
    def performance_config(self):
        """Configuration optimized for performance testing."""
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
                'enable_parallel': True,
                'max_workers': 4,
                'enable_monitoring': True,
                'frame_skip_threshold': 0.033
            },
            'cache': {
                'enabled': True,
                'memory': {'max_size': 1000, 'default_ttl': 300},
                'redis': {'enabled': False},
                'file': {'enabled': True, 'cache_dir': 'cache/detector'}
            }
        }

    @pytest.fixture
    def benchmark_detector(self, performance_config):
        """Create detector for benchmarking."""
        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=0.8)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="BENCH123"):
            detector = LicensePlateDetector(performance_config)
            return detector

    def test_frame_processing_latency(self, benchmark, benchmark_detector):
        """Benchmark frame processing latency."""
        def process_single_frame():
            return benchmark_detector.process_frame()

        # Benchmark the operation
        result = benchmark(process_single_frame)

        # Verify result
        assert result == "BENCH123"

        # Performance assertions (adjust thresholds based on system capabilities)
        assert result.stats.mean < 1.0  # Should complete in less than 1 second
        assert result.stats.stddev < 0.1  # Low variance in performance

    def test_batch_frame_processing(self, benchmark, benchmark_detector):
        """Benchmark batch frame processing."""
        def process_batch_frames():
            results = []
            for _ in range(10):
                result = benchmark_detector.process_frame()
                results.append(result)
            return results

        result = benchmark(process_batch_frames)

        # Verify results
        assert len(result) == 10
        assert all(r == "BENCH123" for r in result)

        # Performance assertions
        assert result.stats.mean < 5.0  # Batch should complete in reasonable time

    def test_memory_usage_during_processing(self, benchmark_detector):
        """Test memory usage during frame processing."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process multiple frames
        for _ in range(50):
            benchmark_detector.process_frame()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory should not grow excessively (adjust threshold as needed)
        assert memory_increase < 50  # Less than 50MB increase

    def test_cache_performance_impact(self, benchmark):
        """Benchmark cache performance impact."""
        config_no_cache = {
            'camera_id': 0,
            'frame_width': 640,
            'frame_height': 480,
            'save_images': False,
            'use_onvif': True,
            'mock_mode': False,
            'ocr_method': 'tesseract',
            'cache': {'enabled': False}
        }

        config_with_cache = config_no_cache.copy()
        config_with_cache['cache'] = {
            'enabled': True,
            'memory': {'max_size': 1000},
            'redis': {'enabled': False},
            'file': {'enabled': True}
        }

        mock_camera = MockONVIFCamera()

        # Test without cache
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=None), \
             patch('pytesseract.image_to_string', return_value="NOCACHE"):
            detector_no_cache = LicensePlateDetector(config_no_cache)

        # Test with cache
        mock_cache = MockCacheManager(enabled=True, hit_rate=0.9)
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="WITHCACHE"):
            detector_with_cache = LicensePlateDetector(config_with_cache)

        def benchmark_no_cache():
            return detector_no_cache.process_frame()

        def benchmark_with_cache():
            return detector_with_cache.process_frame()

        # Benchmark both scenarios
        result_no_cache = benchmark(benchmark_no_cache)
        result_with_cache = benchmark(benchmark_with_cache)

        # Cache should improve performance (lower mean time)
        # Note: In practice, this may vary based on cache hit rate and system
        assert result_with_cache.stats.mean <= result_no_cache.stats.mean * 1.1  # Allow 10% variance

    def test_parallel_vs_sequential_processing(self, benchmark):
        """Benchmark parallel vs sequential processing."""
        base_config = {
            'camera_id': 0,
            'frame_width': 640,
            'frame_height': 480,
            'save_images': False,
            'use_onvif': True,
            'mock_mode': False,
            'ocr_method': 'tesseract',
            'cache': {'enabled': False}
        }

        # Sequential config
        config_sequential = base_config.copy()
        config_sequential['performance'] = {
            'enable_parallel': False,
            'max_workers': 1
        }

        # Parallel config
        config_parallel = base_config.copy()
        config_parallel['performance'] = {
            'enable_parallel': True,
            'max_workers': 4
        }

        mock_camera = MockONVIFCamera()

        # Create detectors
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('pytesseract.image_to_string', return_value="SEQ"):
            detector_seq = LicensePlateDetector(config_sequential)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('pytesseract.image_to_string', return_value="PAR"):
            detector_par = LicensePlateDetector(config_parallel)

        def benchmark_sequential():
            results = []
            for _ in range(5):
                result = detector_seq.process_frame()
                results.append(result)
            return results

        def benchmark_parallel():
            results = []
            for _ in range(5):
                result = detector_par.process_frame()
                results.append(result)
            return results

        result_seq = benchmark(benchmark_sequential)
        result_par = benchmark(benchmark_parallel)

        # Parallel should be faster for multiple frames
        # (Allow some variance due to system differences)
        assert result_par.stats.mean <= result_seq.stats.mean * 1.2

    def test_frame_rate_processing(self, benchmark):
        """Test processing at target frame rates."""
        config = {
            'camera_id': 0,
            'frame_width': 640,
            'frame_height': 480,
            'save_images': False,
            'use_onvif': True,
            'mock_mode': False,
            'ocr_method': 'tesseract',
            'performance': {
                'frame_skip_threshold': 0.033,  # ~30 FPS
                'enable_parallel': True,
                'max_workers': 2
            },
            'cache': {'enabled': True}
        }

        mock_camera = MockONVIFCamera()
        mock_cache = MockCacheManager(enabled=True, hit_rate=0.7)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="FPS30"):

            detector = LicensePlateDetector(config)

            def process_at_frame_rate():
                # Simulate 30 FPS processing
                results = []
                for _ in range(30):  # 1 second of frames
                    result = detector.process_frame()
                    results.append(result)
                    # Small delay to simulate frame timing
                    time.sleep(0.001)
                return results

            result = benchmark(process_at_frame_rate)

            # Should maintain reasonable performance at target frame rate
            assert result.stats.mean < 2.0  # Should complete within 2 seconds

    def test_memory_buffer_efficiency(self, benchmark):
        """Test memory buffer efficiency."""
        config_with_buffers = {
            'camera_id': 0,
            'frame_width': 640,
            'frame_height': 480,
            'save_images': False,
            'use_onvif': True,
            'mock_mode': False,
            'ocr_method': 'tesseract',
            'performance': {
                'enable_buffer_prealloc': True,
                'enable_parallel': False
            },
            'cache': {'enabled': False}
        }

        config_without_buffers = config_with_buffers.copy()
        config_without_buffers['performance']['enable_buffer_prealloc'] = False

        mock_camera = MockONVIFCamera()

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('pytesseract.image_to_string', return_value="BUF"):
            detector_with_buffers = LicensePlateDetector(config_with_buffers)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('pytesseract.image_to_string', return_value="NOBUF"):
            detector_without_buffers = LicensePlateDetector(config_without_buffers)

        def benchmark_with_buffers():
            for _ in range(20):
                detector_with_buffers.process_frame()

        def benchmark_without_buffers():
            for _ in range(20):
                detector_without_buffers.process_frame()

        result_with = benchmark(benchmark_with_buffers)
        result_without = benchmark(benchmark_without_buffers)

        # Buffers should improve performance
        assert result_with.stats.mean <= result_without.stats.mean

    def test_large_frame_processing(self, benchmark):
        """Test processing of large frames."""
        config = {
            'camera_id': 0,
            'frame_width': 1920,  # 1080p width
            'frame_height': 1080,  # 1080p height
            'save_images': False,
            'use_onvif': True,
            'mock_mode': False,
            'ocr_method': 'tesseract',
            'performance': {
                'enable_buffer_prealloc': True,
                'enable_parallel': True,
                'max_workers': 4
            },
            'cache': {'enabled': True}
        }

        # Create large mock camera
        mock_camera = MockONVIFCamera(frame_width=1920, frame_height=1080)
        mock_cache = MockCacheManager(enabled=True)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache), \
             patch('pytesseract.image_to_string', return_value="LARGE"):
            detector = LicensePlateDetector(config)

            def process_large_frame():
                return detector.process_frame()

            result = benchmark(process_large_frame)

            # Large frame processing should still be reasonable
            assert result.stats.mean < 5.0  # Should complete in less than 5 seconds

    def test_concurrent_frame_processing(self, benchmark):
        """Test concurrent frame processing performance."""
        import concurrent.futures

        config = {
            'camera_id': 0,
            'frame_width': 640,
            'frame_height': 480,
            'save_images': False,
            'use_onvif': True,
            'mock_mode': False,
            'ocr_method': 'tesseract',
            'performance': {
                'enable_parallel': True,
                'max_workers': 4
            },
            'cache': {'enabled': False}
        }

        mock_camera = MockONVIFCamera()
        detectors = []

        # Create multiple detector instances
        for _ in range(4):
            with patch('src.recognition.onvif_camera.init_camera_manager', return_value=MockONVIFCamera()), \
                 patch('pytesseract.image_to_string', return_value=f"CONC{i}"):
                detector = LicensePlateDetector(config)
                detectors.append(detector)

        def process_concurrent_frames():
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(detector.process_frame) for detector in detectors]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            return results

        result = benchmark(process_concurrent_frames)

        # Concurrent processing should be efficient
        assert len(result) == 4
        assert result.stats.mean < 3.0  # Should complete within 3 seconds

    def test_cache_hit_rate_impact(self, benchmark):
        """Test impact of different cache hit rates."""
        base_config = {
            'camera_id': 0,
            'frame_width': 640,
            'frame_height': 480,
            'save_images': False,
            'use_onvif': True,
            'mock_mode': False,
            'ocr_method': 'tesseract',
            'cache': {'enabled': True}
        }

        mock_camera = MockONVIFCamera()

        # Test with low hit rate
        mock_cache_low = MockCacheManager(enabled=True, hit_rate=0.2)
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache_low), \
             patch('pytesseract.image_to_string', return_value="LOW"):
            detector_low = LicensePlateDetector(base_config)

        # Test with high hit rate
        mock_cache_high = MockCacheManager(enabled=True, hit_rate=0.9)
        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.cache.cache_manager.CacheManager', return_value=mock_cache_high), \
             patch('pytesseract.image_to_string', return_value="HIGH"):
            detector_high = LicensePlateDetector(base_config)

        def benchmark_low_hit_rate():
            for _ in range(20):
                detector_low.process_frame()

        def benchmark_high_hit_rate():
            for _ in range(20):
                detector_high.process_frame()

        result_low = benchmark(benchmark_low_hit_rate)
        result_high = benchmark(benchmark_high_hit_rate)

        # High hit rate should be faster
        assert result_high.stats.mean < result_low.stats.mean

    def test_ocr_method_performance_comparison(self, benchmark):
        """Compare performance of different OCR methods."""
        base_config = {
            'camera_id': 0,
            'frame_width': 640,
            'frame_height': 480,
            'save_images': False,
            'use_onvif': True,
            'mock_mode': False,
            'cache': {'enabled': False}
        }

        mock_camera = MockONVIFCamera()

        # Tesseract config
        config_tesseract = base_config.copy()
        config_tesseract['ocr_method'] = 'tesseract'

        # Deep learning config (mocked)
        config_dl = base_config.copy()
        config_dl['ocr_method'] = 'deep_learning'

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('pytesseract.image_to_string', return_value="TESS"):
            detector_tesseract = LicensePlateDetector(config_tesseract)

        with patch('src.recognition.onvif_camera.init_camera_manager', return_value=mock_camera), \
             patch('src.recognition.detector_fixed.TENSORFLOW_AVAILABLE', True), \
             patch.object(LicensePlateDetector, '_deep_learning_ocr', return_value="DL"):
            detector_dl = LicensePlateDetector(config_dl)

        def benchmark_tesseract():
            return detector_tesseract.process_frame()

        def benchmark_deep_learning():
            return detector_dl.process_frame()

        result_tess = benchmark(benchmark_tesseract)
        result_dl = benchmark(benchmark_deep_learning)

        # Both should complete in reasonable time
        assert result_tess.stats.mean < 2.0
        assert result_dl.stats.mean < 2.0

    def test_system_resource_monitoring(self, benchmark_detector):
        """Monitor system resources during processing."""
        process = psutil.Process()

        initial_cpu = psutil.cpu_percent(interval=None)
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run benchmark
        def intensive_processing():
            results = []
            for _ in range(100):
                result = benchmark_detector.process_frame()
                results.append(result)
            return results

        result = benchmark(intensive_processing)

        final_cpu = psutil.cpu_percent(interval=None)
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        cpu_increase = final_cpu - initial_cpu
        memory_increase = final_memory - initial_memory

        # Resource usage should be reasonable
        assert cpu_increase < 50  # Less than 50% CPU increase
        assert memory_increase < 100  # Less than 100MB memory increase
        assert result.stats.mean < 10  # Should complete within 10 seconds