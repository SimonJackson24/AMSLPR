"""
Multi-tier cache manager that orchestrates different cache types.
Provides unified interface and intelligent cache hierarchy management.
"""

import time
import logging
from typing import Any, Optional, Dict, List
from .memory_cache import MemoryCache
from .redis_cache import RedisCache
from .file_cache import FileCache
from .result_cache import ResultCache

logger = logging.getLogger('VisiGate.cache')

class CacheManager:
    """
    Multi-tier cache manager with intelligent hierarchy:
    1. Memory Cache (L1) - Fastest, limited size
    2. Redis Cache (L2) - Distributed, medium speed
    3. File Cache (L3) - Persistent, slowest
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}

        # Initialize caches based on configuration
        self._init_caches()

        # Specialized result cache
        self.result_cache = ResultCache(
            memory_cache=self.memory_cache,
            redis_cache=self.redis_cache,
            file_cache=self.file_cache,
            confidence_threshold=self.config.get('confidence_threshold', 0.8)
        )

        # Cache hierarchy configuration
        self.enable_hierarchy = self.config.get('enable_hierarchy', True)
        self.promote_on_hit = self.config.get('promote_on_hit', True)

        logger.info("Cache manager initialized")

    def _init_caches(self):
        """Initialize cache instances based on configuration."""
        # Memory cache configuration
        memory_config = self.config.get('memory', {})
        self.memory_cache = MemoryCache(
            max_size=memory_config.get('max_size', 1000),
            default_ttl=memory_config.get('default_ttl', 300)
        )

        # Redis cache configuration
        redis_config = self.config.get('redis', {})
        if redis_config.get('enabled', False):
            try:
                self.redis_cache = RedisCache(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    db=redis_config.get('db', 0),
                    password=redis_config.get('password'),
                    max_size=redis_config.get('max_size', 10000),
                    default_ttl=redis_config.get('default_ttl', 600),
                    serialization=redis_config.get('serialization', 'json')
                )
                if not self.redis_cache.is_connected():
                    logger.warning("Redis cache initialization failed, disabling Redis")
                    self.redis_cache = None
            except Exception as e:
                logger.error(f"Failed to initialize Redis cache: {e}")
                self.redis_cache = None
        else:
            self.redis_cache = None

        # File cache configuration
        file_config = self.config.get('file', {})
        if file_config.get('enabled', True):
            self.file_cache = FileCache(
                cache_dir=file_config.get('cache_dir', 'cache'),
                max_size=file_config.get('max_size', 5000),
                default_ttl=file_config.get('default_ttl', 3600),
                serialization=file_config.get('serialization', 'pickle')
            )
        else:
            self.file_cache = None

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache hierarchy."""
        # Try memory cache first
        value = self.memory_cache.get(key)
        if value is not None:
            return value

        # Try Redis cache
        if self.redis_cache and self.redis_cache.is_connected():
            value = self.redis_cache.get(key)
            if value is not None:
                # Promote to memory cache
                if self.promote_on_hit:
                    self.memory_cache.set(key, value, self.memory_cache.default_ttl)
                return value

        # Try file cache
        if self.file_cache:
            value = self.file_cache.get(key)
            if value is not None:
                # Promote to memory cache
                if self.promote_on_hit:
                    self.memory_cache.set(key, value, self.memory_cache.default_ttl)
                return value

        return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in cache hierarchy."""
        success = True

        # Always try memory cache
        if not self.memory_cache.set(key, value, ttl):
            success = False

        # Try Redis cache
        if self.redis_cache and self.redis_cache.is_connected():
            if not self.redis_cache.set(key, value, ttl):
                logger.warning("Failed to set value in Redis cache")

        # Try file cache for persistence
        if self.file_cache:
            if not self.file_cache.set(key, value, ttl):
                logger.warning("Failed to set value in file cache")

        return success

    def delete(self, key: str) -> bool:
        """Delete value from all caches."""
        success = True

        # Delete from memory
        if not self.memory_cache.delete(key):
            success = False

        # Delete from Redis
        if self.redis_cache:
            if not self.redis_cache.delete(key):
                logger.warning("Failed to delete from Redis cache")

        # Delete from file
        if self.file_cache:
            if not self.file_cache.delete(key):
                logger.warning("Failed to delete from file cache")

        return success

    def clear(self) -> bool:
        """Clear all caches."""
        success = True

        if not self.memory_cache.clear():
            success = False

        if self.redis_cache:
            if not self.redis_cache.clear():
                logger.warning("Failed to clear Redis cache")

        if self.file_cache:
            if not self.file_cache.clear():
                logger.warning("Failed to clear file cache")

        return success

    def has_key(self, key: str) -> bool:
        """Check if key exists in any cache."""
        if self.memory_cache.has_key(key):
            return True

        if self.redis_cache and self.redis_cache.has_key(key):
            return True

        if self.file_cache and self.file_cache.has_key(key):
            return True

        return False

    def get_or_set(self, key: str, default_func, ttl: Optional[float] = None):
        """Get from cache or compute and set."""
        value = self.get(key)
        if value is not None:
            return value

        value = default_func()
        self.set(key, value, ttl)
        return value

    # Specialized methods for different data types

    def cache_ocr_result(self, image_data, text: str, confidence: float) -> bool:
        """Cache OCR result with specialized handling."""
        from .result_cache import OCRResult
        result = OCRResult(text, confidence)
        return self.result_cache.cache_ocr_result(image_data, result)

    def get_ocr_result(self, image_data):
        """Get cached OCR result."""
        return self.result_cache.get_ocr_result(image_data)

    def cache_plate_text(self, plate_text: str, confidence: float, metadata: Dict = None) -> bool:
        """Cache license plate text."""
        return self.result_cache.cache_plate_text(plate_text, confidence, metadata)

    def get_similar_plates(self, plate_text: str) -> List[Dict]:
        """Get similar cached plates."""
        return self.result_cache.get_similar_plates(plate_text)

    def cache_image_preprocessing(self, image_data, processed_data: Any) -> bool:
        """Cache image preprocessing results."""
        return self.result_cache.cache_image_preprocessing(image_data, processed_data)

    def get_image_preprocessing(self, image_data) -> Optional[Any]:
        """Get cached image preprocessing result."""
        return self.result_cache.get_image_preprocessing(image_data)

    def get_stats(self) -> Dict:
        """Get comprehensive cache statistics."""
        stats = {
            'hierarchy_enabled': self.enable_hierarchy,
            'promote_on_hit': self.promote_on_hit,
            'memory': self.memory_cache.get_stats(),
            'result_cache': self.result_cache.get_cache_stats()
        }

        if self.redis_cache:
            stats['redis'] = {
                'connected': self.redis_cache.is_connected(),
                'size': self.redis_cache.size(),
                'metrics': self.redis_cache.get_metrics()
            }
        else:
            stats['redis'] = {'enabled': False}

        if self.file_cache:
            stats['file'] = {
                'size': self.file_cache.size(),
                'disk_usage': self.file_cache.get_disk_usage(),
                'metrics': self.file_cache.get_metrics()
            }
        else:
            stats['file'] = {'enabled': False}

        return stats

    def warmup_cache(self, common_plates: List[str] = None):
        """Warm up cache with common data."""
        if common_plates:
            self.result_cache.warmup_cache(common_plates)

    def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        # This is a simplified implementation
        # In a real system, you'd want more sophisticated pattern matching
        keys_to_delete = []

        # Check memory cache
        for key in self.memory_cache.keys():
            if pattern in key:
                keys_to_delete.append(key)

        # Delete matching keys
        for key in keys_to_delete:
            self.delete(key)

    def health_check(self) -> Dict:
        """Perform health check on all caches."""
        health = {
            'memory': {
                'healthy': True,
                'size': self.memory_cache.size()
            },
            'redis': {
                'healthy': False,
                'connected': False
            },
            'file': {
                'healthy': False,
                'size': 0
            }
        }

        # Check Redis
        if self.redis_cache:
            health['redis']['connected'] = self.redis_cache.is_connected()
            health['redis']['healthy'] = health['redis']['connected']
            if health['redis']['connected']:
                try:
                    health['redis']['size'] = self.redis_cache.size()
                except:
                    health['redis']['healthy'] = False

        # Check file cache
        if self.file_cache:
            try:
                health['file']['size'] = self.file_cache.size()
                health['file']['healthy'] = True
            except Exception as e:
                logger.error(f"File cache health check failed: {e}")

        return health