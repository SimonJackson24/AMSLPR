"""
Base cache interface and utilities for VisiGate caching system.
"""

import abc
import time
import threading
import logging
from typing import Any, Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger('VisiGate.cache')

@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    key: str
    value: Any
    timestamp: float
    ttl: Optional[float] = None
    access_count: int = 0
    last_access: float = 0

    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def touch(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_access = time.time()

class BaseCache(abc.ABC):
    """
    Abstract base class for all cache implementations.
    Provides common interface and thread-safety.
    """

    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
        self._metrics = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0,
            'size': 0
        }
        self._metrics_lock = threading.Lock()

    @abc.abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        pass

    @abc.abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set a value in the cache."""
        pass

    @abc.abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        pass

    @abc.abstractmethod
    def clear(self) -> bool:
        """Clear all values from the cache."""
        pass

    @abc.abstractmethod
    def size(self) -> int:
        """Get the current size of the cache."""
        pass

    def get_or_set(self, key: str, default_func, ttl: Optional[float] = None):
        """
        Get a value from cache, or compute and set it if not found.

        Args:
            key: Cache key
            default_func: Function to compute value if not cached
            ttl: Time to live for the cached value

        Returns:
            The cached or computed value
        """
        value = self.get(key)
        if value is not None:
            return value

        value = default_func()
        self.set(key, value, ttl)
        return value

    def get_metrics(self) -> Dict[str, int]:
        """Get cache performance metrics."""
        with self._metrics_lock:
            return self._metrics.copy()

    def reset_metrics(self):
        """Reset performance metrics."""
        with self._metrics_lock:
            self._metrics = {k: 0 for k in self._metrics.keys()}

    def _record_hit(self):
        """Record a cache hit."""
        with self._metrics_lock:
            self._metrics['hits'] += 1

    def _record_miss(self):
        """Record a cache miss."""
        with self._metrics_lock:
            self._metrics['misses'] += 1

    def _record_set(self):
        """Record a cache set operation."""
        with self._metrics_lock:
            self._metrics['sets'] += 1

    def _record_delete(self):
        """Record a cache delete operation."""
        with self._metrics_lock:
            self._metrics['deletes'] += 1

    def _record_eviction(self):
        """Record a cache eviction."""
        with self._metrics_lock:
            self._metrics['evictions'] += 1

    def _update_size(self, size: int):
        """Update the current cache size."""
        with self._metrics_lock:
            self._metrics['size'] = size

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        with self._metrics_lock:
            total = self._metrics['hits'] + self._metrics['misses']
            return self._metrics['hits'] / total if total > 0 else 0.0

class CacheError(Exception):
    """Base exception for cache operations."""
    pass

class CacheConnectionError(CacheError):
    """Exception raised when cache connection fails."""
    pass

class CacheSerializationError(CacheError):
    """Exception raised when serialization/deserialization fails."""
    pass