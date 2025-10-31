"""
In-memory LRU (Least Recently Used) cache implementation.
Thread-safe and efficient for frequently accessed data.
"""

import time
import threading
from collections import OrderedDict
from typing import Any, Optional, Dict
from .base_cache import BaseCache, CacheEntry

class MemoryCache(BaseCache):
    """
    In-memory LRU cache implementation using OrderedDict for O(1) operations.
    Thread-safe with configurable size and TTL support.
    """

    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        super().__init__(max_size, default_ttl)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._cleanup_interval = 60  # seconds
        self._last_cleanup = time.time()
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()

        # Start background cleanup thread
        self._start_cleanup_thread()

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        with self._lock:
            self._cleanup_expired()
            entry = self._cache.get(key)

            if entry is None:
                self._record_miss()
                return None

            if entry.is_expired():
                self._cache.pop(key, None)
                self._record_miss()
                self._record_eviction()
                self._update_size(len(self._cache))
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self._record_hit()
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set a value in the cache."""
        with self._lock:
            self._cleanup_expired()

            ttl = ttl or self.default_ttl
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                ttl=ttl
            )

            # Check if key exists
            exists = key in self._cache
            if exists:
                # Update existing entry
                self._cache[key] = entry
                self._cache.move_to_end(key)
            else:
                # Add new entry
                if len(self._cache) >= self.max_size:
                    # Evict least recently used
                    evicted_key, _ = self._cache.popitem(last=False)
                    self._record_eviction()

                self._cache[key] = entry

            self._record_set()
            self._update_size(len(self._cache))
            return True

    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._record_delete()
                self._update_size(len(self._cache))
                return True
            return False

    def clear(self) -> bool:
        """Clear all values from the cache."""
        with self._lock:
            self._cache.clear()
            self._update_size(0)
            return True

    def size(self) -> int:
        """Get the current size of the cache."""
        with self._lock:
            self._cleanup_expired()
            return len(self._cache)

    def keys(self) -> list:
        """Get all cache keys."""
        with self._lock:
            self._cleanup_expired()
            return list(self._cache.keys())

    def has_key(self, key: str) -> bool:
        """Check if key exists in cache."""
        with self._lock:
            self._cleanup_expired()
            entry = self._cache.get(key)
            if entry is None or entry.is_expired():
                return False
            return True

    def get_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        with self._lock:
            self._cleanup_expired()
            stats = {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': self.hit_rate,
                'metrics': self.get_metrics(),
                'oldest_entry': None,
                'newest_entry': None
            }

            if self._cache:
                # Find oldest and newest entries
                entries = list(self._cache.values())
                oldest = min(entries, key=lambda e: e.timestamp)
                newest = max(entries, key=lambda e: e.timestamp)

                stats['oldest_entry'] = {
                    'key': oldest.key,
                    'age': time.time() - oldest.timestamp,
                    'ttl': oldest.ttl
                }
                stats['newest_entry'] = {
                    'key': newest.key,
                    'age': time.time() - newest.timestamp,
                    'ttl': newest.ttl
                }

            return stats

    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            self._cache.pop(key, None)
            self._record_eviction()

        self._last_cleanup = current_time
        if expired_keys:
            self._update_size(len(self._cache))

    def _start_cleanup_thread(self):
        """Start background cleanup thread."""
        def cleanup_worker():
            while not self._stop_cleanup.is_set():
                self._stop_cleanup.wait(self._cleanup_interval)
                if not self._stop_cleanup.is_set():
                    with self._lock:
                        self._cleanup_expired()

        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, '_stop_cleanup'):
            self._stop_cleanup.set()
        if hasattr(self, '_cleanup_thread') and self._cleanup_thread:
            self._cleanup_thread.join(timeout=1.0)