"""
File-based persistent cache implementation.
Stores cache data in files for persistence across restarts.
"""

import os
import json
import pickle
import time
import hashlib
import threading
import logging
from pathlib import Path
from typing import Any, Optional, Dict, List
from .base_cache import BaseCache, CacheEntry, CacheSerializationError

logger = logging.getLogger('AMSLPR.cache')

class FileCache(BaseCache):
    """
    File-based cache that persists data to disk.
    Uses JSON for metadata and configurable serialization for values.
    """

    def __init__(self,
                 cache_dir: str = 'cache',
                 max_size: int = 1000,
                 default_ttl: Optional[float] = None,
                 serialization: str = 'pickle',
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 cleanup_interval: int = 300):  # 5 minutes
        super().__init__(max_size, default_ttl)

        self.cache_dir = Path(cache_dir)
        self.serialization = serialization
        self.max_file_size = max_file_size
        self.cleanup_interval = cleanup_interval

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Metadata file
        self.metadata_file = self.cache_dir / 'metadata.json'

        # Load existing metadata
        self._metadata = self._load_metadata()

        # Background cleanup
        self._last_cleanup = time.time()
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        self._start_cleanup_thread()

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for a cache key."""
        # Create a safe filename from key
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for file storage."""
        try:
            if self.serialization == 'json':
                return json.dumps(value).encode('utf-8')
            elif self.serialization == 'pickle':
                return pickle.dumps(value)
            else:
                raise ValueError(f"Unsupported serialization: {self.serialization}")
        except Exception as e:
            raise CacheSerializationError(f"Serialization failed: {e}")

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from file storage."""
        try:
            if self.serialization == 'json':
                return json.loads(data.decode('utf-8'))
            elif self.serialization == 'pickle':
                return pickle.loads(data)
            else:
                raise ValueError(f"Unsupported serialization: {self.serialization}")
        except Exception as e:
            raise CacheSerializationError(f"Deserialization failed: {e}")

    def _load_metadata(self) -> Dict[str, Dict]:
        """Load cache metadata from file."""
        if not self.metadata_file.exists():
            return {}

        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
                # Convert back to CacheEntry objects
                metadata = {}
                for key, entry_data in data.items():
                    metadata[key] = CacheEntry(
                        key=key,
                        value=None,  # Will be loaded from file when needed
                        timestamp=entry_data['timestamp'],
                        ttl=entry_data.get('ttl'),
                        access_count=entry_data.get('access_count', 0),
                        last_access=entry_data.get('last_access', entry_data['timestamp'])
                    )
                return metadata
        except Exception as e:
            logger.error(f"Failed to load cache metadata: {e}")
            return {}

    def _save_metadata(self):
        """Save cache metadata to file."""
        try:
            data = {}
            for key, entry in self._metadata.items():
                data[key] = {
                    'timestamp': entry.timestamp,
                    'ttl': entry.ttl,
                    'access_count': entry.access_count,
                    'last_access': entry.last_access
                }

            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Get a value from file cache."""
        with self._lock:
            self._cleanup_expired()
            entry = self._metadata.get(key)

            if entry is None:
                self._record_miss()
                return None

            if entry.is_expired():
                self._delete_entry(key)
                self._record_miss()
                self._record_eviction()
                return None

            # Load value from file
            cache_path = self._get_cache_path(key)
            if not cache_path.exists():
                self._delete_entry(key)
                self._record_miss()
                return None

            try:
                with open(cache_path, 'rb') as f:
                    data = f.read()
                    value = self._deserialize(data)

                entry.touch()
                self._record_hit()
                return value
            except (FileNotFoundError, CacheSerializationError) as e:
                logger.warning(f"Failed to load cached value for key {key}: {e}")
                self._delete_entry(key)
                self._record_miss()
                return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set a value in file cache."""
        with self._lock:
            self._cleanup_expired()

            ttl = ttl or self.default_ttl
            cache_path = self._get_cache_path(key)

            try:
                # Serialize value
                data = self._serialize(value)

                # Check file size limit
                if len(data) > self.max_file_size:
                    logger.warning(f"Value too large for file cache: {len(data)} bytes")
                    return False

                # Write to file
                with open(cache_path, 'wb') as f:
                    f.write(data)

                # Update metadata
                entry = CacheEntry(
                    key=key,
                    value=None,  # Not stored in memory
                    timestamp=time.time(),
                    ttl=ttl
                )

                exists = key in self._metadata
                self._metadata[key] = entry

                # Check size limit
                if len(self._metadata) > self.max_size:
                    self._evict_lru()

                self._save_metadata()
                self._record_set()
                return True

            except Exception as e:
                logger.error(f"Failed to set cache value for key {key}: {e}")
                # Clean up partial files
                if cache_path.exists():
                    try:
                        cache_path.unlink()
                    except:
                        pass
                return False

    def delete(self, key: str) -> bool:
        """Delete a value from file cache."""
        with self._lock:
            if self._delete_entry(key):
                self._save_metadata()
                self._record_delete()
                return True
            return False

    def clear(self) -> bool:
        """Clear all values from file cache."""
        with self._lock:
            try:
                # Remove all cache files
                for cache_file in self.cache_dir.glob('*.cache'):
                    cache_file.unlink()

                # Clear metadata
                self._metadata.clear()
                self._save_metadata()
                return True
            except Exception as e:
                logger.error(f"Failed to clear file cache: {e}")
                return False

    def size(self) -> int:
        """Get the current size of the file cache."""
        with self._lock:
            self._cleanup_expired()
            return len(self._metadata)

    def keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            self._cleanup_expired()
            return list(self._metadata.keys())

    def has_key(self, key: str) -> bool:
        """Check if key exists in cache."""
        with self._lock:
            self._cleanup_expired()
            entry = self._metadata.get(key)
            if entry is None or entry.is_expired():
                return False

            # Check if file exists
            cache_path = self._get_cache_path(key)
            return cache_path.exists()

    def get_disk_usage(self) -> Dict[str, int]:
        """Get disk usage statistics."""
        total_size = 0
        file_count = 0

        try:
            for cache_file in self.cache_dir.glob('*.cache'):
                if cache_file.exists():
                    total_size += cache_file.stat().st_size
                    file_count += 1
        except Exception as e:
            logger.error(f"Failed to calculate disk usage: {e}")

        return {
            'total_size_bytes': total_size,
            'file_count': file_count,
            'metadata_size_bytes': self.metadata_file.stat().st_size if self.metadata_file.exists() else 0
        }

    def _delete_entry(self, key: str) -> bool:
        """Delete a cache entry and its file."""
        entry = self._metadata.pop(key, None)
        if entry is None:
            return False

        cache_path = self._get_cache_path(key)
        try:
            if cache_path.exists():
                cache_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache file for key {key}: {e}")
            return False

    def _evict_lru(self):
        """Evict least recently used entries."""
        if not self._metadata:
            return

        # Find LRU entry
        lru_key = min(self._metadata.keys(),
                     key=lambda k: self._metadata[k].last_access)

        self._delete_entry(lru_key)
        self._record_eviction()

    def _cleanup_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        if current_time - self._last_cleanup < self.cleanup_interval:
            return

        expired_keys = []
        for key, entry in self._metadata.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            self._delete_entry(key)
            self._record_eviction()

        if expired_keys:
            self._save_metadata()

        self._last_cleanup = current_time

    def _start_cleanup_thread(self):
        """Start background cleanup thread."""
        def cleanup_worker():
            while not self._stop_cleanup.is_set():
                self._stop_cleanup.wait(self.cleanup_interval)
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