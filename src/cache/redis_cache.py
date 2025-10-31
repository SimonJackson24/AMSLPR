"""
Redis-based distributed cache implementation.
Provides shared caching across multiple detector instances.
"""

import json
import pickle
import time
import logging
from typing import Any, Optional, Dict
from .base_cache import BaseCache, CacheConnectionError, CacheSerializationError

logger = logging.getLogger('AMSLPR.cache')

class RedisCache(BaseCache):
    """
    Redis cache implementation with connection pooling and graceful fallback.
    Supports JSON and pickle serialization.
    """

    def __init__(self,
                 host: str = 'localhost',
                 port: int = 6379,
                 db: int = 0,
                 password: Optional[str] = None,
                 max_size: int = 10000,
                 default_ttl: Optional[float] = None,
                 connection_timeout: float = 5.0,
                 max_connections: int = 10,
                 serialization: str = 'json'):
        super().__init__(max_size, default_ttl)

        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.connection_timeout = connection_timeout
        self.max_connections = max_connections
        self.serialization = serialization

        self._redis = None
        self._connected = False
        self._connect()

    def _connect(self):
        """Establish Redis connection with error handling."""
        try:
            import redis
            self._redis = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                socket_timeout=self.connection_timeout,
                socket_connect_timeout=self.connection_timeout,
                decode_responses=False  # We'll handle decoding ourselves
            )
            # Test connection
            with self._redis.get_connection() as conn:
                conn.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except ImportError:
            logger.warning("Redis library not available, Redis cache disabled")
            self._connected = False
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False

    def _ensure_connection(self):
        """Ensure Redis connection is available."""
        if not self._connected:
            self._connect()
        return self._connected

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for Redis storage."""
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
        """Deserialize value from Redis storage."""
        try:
            if self.serialization == 'json':
                return json.loads(data.decode('utf-8'))
            elif self.serialization == 'pickle':
                return pickle.loads(data)
            else:
                raise ValueError(f"Unsupported serialization: {self.serialization}")
        except Exception as e:
            raise CacheSerializationError(f"Deserialization failed: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis cache."""
        if not self._ensure_connection():
            self._record_miss()
            return None

        try:
            with self._redis.get_connection() as conn:
                data = conn.get(key)
                if data is None:
                    self._record_miss()
                    return None

                value = self._deserialize(data)
                self._record_hit()
                return value
        except CacheSerializationError:
            # Remove corrupted data
            self.delete(key)
            self._record_miss()
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self._connected = False
            self._record_miss()
            return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set a value in Redis cache."""
        if not self._ensure_connection():
            return False

        try:
            data = self._serialize(value)
            ttl = ttl or self.default_ttl

            with self._redis.get_connection() as conn:
                if ttl:
                    result = conn.setex(key, int(ttl), data)
                else:
                    result = conn.set(key, data)

                if result:
                    self._record_set()
                    return True
                return False
        except CacheSerializationError as e:
            logger.error(f"Serialization error in set: {e}")
            return False
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            self._connected = False
            return False

    def delete(self, key: str) -> bool:
        """Delete a value from Redis cache."""
        if not self._ensure_connection():
            return False

        try:
            with self._redis.get_connection() as conn:
                result = conn.delete(key)
                if result > 0:
                    self._record_delete()
                    return True
                return False
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            self._connected = False
            return False

    def clear(self) -> bool:
        """Clear all values from Redis cache."""
        if not self._ensure_connection():
            return False

        try:
            with self._redis.get_connection() as conn:
                result = conn.flushdb()
                return result
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            self._connected = False
            return False

    def size(self) -> int:
        """Get the current size of the Redis cache."""
        if not self._ensure_connection():
            return 0

        try:
            with self._redis.get_connection() as conn:
                return conn.dbsize()
        except Exception as e:
            logger.error(f"Redis size error: {e}")
            self._connected = False
            return 0

    def keys(self, pattern: str = "*") -> list:
        """Get keys matching pattern."""
        if not self._ensure_connection():
            return []

        try:
            with self._redis.get_connection() as conn:
                return conn.keys(pattern)
        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            self._connected = False
            return []

    def has_key(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self._ensure_connection():
            return False

        try:
            with self._redis.get_connection() as conn:
                return conn.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            self._connected = False
            return False

    def get_ttl(self, key: str) -> Optional[float]:
        """Get TTL for a key."""
        if not self._ensure_connection():
            return None

        try:
            with self._redis.get_connection() as conn:
                ttl = conn.ttl(key)
                return ttl if ttl > 0 else None
        except Exception as e:
            logger.error(f"Redis TTL error: {e}")
            self._connected = False
            return None

    def set_multiple(self, key_value_pairs: Dict[str, Any], ttl: Optional[float] = None) -> bool:
        """Set multiple key-value pairs efficiently."""
        if not self._ensure_connection():
            return False

        try:
            ttl = ttl or self.default_ttl
            pipeline_data = {}

            for key, value in key_value_pairs.items():
                pipeline_data[key] = self._serialize(value)

            with self._redis.get_connection() as conn:
                pipe = conn.pipeline()
                pipe.mset(pipeline_data)

                if ttl:
                    for key in key_value_pairs.keys():
                        pipe.expire(key, int(ttl))

                results = pipe.execute()
                success = all(results)
                if success:
                    self._record_set()
                return success
        except Exception as e:
            logger.error(f"Redis set_multiple error: {e}")
            self._connected = False
            return False

    def get_multiple(self, keys: list) -> Dict[str, Any]:
        """Get multiple values efficiently."""
        if not self._ensure_connection():
            return {}

        try:
            with self._redis.get_connection() as conn:
                values = conn.mget(keys)

            result = {}
            for key, data in zip(keys, values):
                if data is not None:
                    try:
                        result[key] = self._deserialize(data)
                    except CacheSerializationError:
                        # Skip corrupted data
                        continue

            self._record_hit()
            return result
        except Exception as e:
            logger.error(f"Redis get_multiple error: {e}")
            self._connected = False
            return {}

    def is_connected(self) -> bool:
        """Check if Redis connection is active."""
        return self._connected

    def reconnect(self):
        """Force reconnection to Redis."""
        self._connected = False
        self._connect()