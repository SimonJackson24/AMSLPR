"""
Specialized cache for OCR results and related data.
Provides intelligent caching based on confidence scores and similarity.
"""

import hashlib
import time
import logging
from typing import Any, Optional, Dict, List, Tuple
from .memory_cache import MemoryCache
from .redis_cache import RedisCache
from .file_cache import FileCache

logger = logging.getLogger('VisiGate.cache')

class OCRResult:
    """Represents an OCR result with metadata."""

    def __init__(self, text: str, confidence: float, timestamp: float = None):
        self.text = text
        self.confidence = confidence
        self.timestamp = timestamp or time.time()
        self.access_count = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'text': self.text,
            'confidence': self.confidence,
            'timestamp': self.timestamp,
            'access_count': self.access_count
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'OCRResult':
        """Create from dictionary."""
        result = cls(data['text'], data['confidence'], data['timestamp'])
        result.access_count = data.get('access_count', 0)
        return result

class ResultCache:
    """
    Specialized cache for OCR results with intelligent caching strategies.
    Uses multi-tier caching with different TTLs based on confidence.
    """

    def __init__(self,
                 memory_cache: Optional[MemoryCache] = None,
                 redis_cache: Optional[RedisCache] = None,
                 file_cache: Optional[FileCache] = None,
                 confidence_threshold: float = 0.8,
                 similarity_threshold: float = 0.9):
        self.confidence_threshold = confidence_threshold
        self.similarity_threshold = similarity_threshold

        # Initialize caches
        self.memory_cache = memory_cache or MemoryCache(max_size=500, default_ttl=300)  # 5 min
        self.redis_cache = redis_cache
        self.file_cache = file_cache or FileCache(cache_dir='cache/ocr_results', max_size=2000, default_ttl=3600)  # 1 hour

        # Cache key prefixes
        self.OCR_PREFIX = "ocr:"
        self.PLATE_PREFIX = "plate:"
        self.IMAGE_PREFIX = "image:"

    def _generate_image_hash(self, image_data) -> str:
        """Generate hash for image data."""
        if hasattr(image_data, 'tobytes'):
            # NumPy array
            data = image_data.tobytes()
        elif isinstance(image_data, bytes):
            data = image_data
        else:
            data = str(image_data).encode()

        return hashlib.md5(data).hexdigest()

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using simple edit distance."""
        if text1 == text2:
            return 1.0

        # Simple character-level similarity
        set1 = set(text1.upper())
        set2 = set(text2.upper())
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    def _get_cache_ttl(self, confidence: float) -> float:
        """Get TTL based on confidence score."""
        if confidence >= 0.95:
            return 1800  # 30 minutes for high confidence
        elif confidence >= 0.85:
            return 900   # 15 minutes for medium confidence
        else:
            return 300   # 5 minutes for low confidence

    def cache_ocr_result(self, image_data, ocr_result: OCRResult) -> bool:
        """Cache OCR result with intelligent TTL."""
        if ocr_result.confidence < self.confidence_threshold:
            return False  # Don't cache low confidence results

        image_hash = self._generate_image_hash(image_data)
        cache_key = f"{self.OCR_PREFIX}{image_hash}"
        ttl = self._get_cache_ttl(ocr_result.confidence)

        # Cache in memory first
        success = self.memory_cache.set(cache_key, ocr_result.to_dict(), ttl)

        # Cache in Redis if available
        if self.redis_cache and self.redis_cache.is_connected():
            self.redis_cache.set(cache_key, ocr_result.to_dict(), ttl)

        # Cache in file for persistence (longer TTL)
        if self.file_cache:
            self.file_cache.set(cache_key, ocr_result.to_dict(), ttl * 2)

        return success

    def get_ocr_result(self, image_data) -> Optional[OCRResult]:
        """Get cached OCR result."""
        image_hash = self._generate_image_hash(image_data)
        cache_key = f"{self.OCR_PREFIX}{image_hash}"

        # Try memory cache first
        result_data = self.memory_cache.get(cache_key)
        if result_data:
            result = OCRResult.from_dict(result_data)
            result.access_count += 1
            # Update access count
            self.memory_cache.set(cache_key, result.to_dict(),
                                self.memory_cache.default_ttl)
            return result

        # Try Redis cache
        if self.redis_cache and self.redis_cache.is_connected():
            result_data = self.redis_cache.get(cache_key)
            if result_data:
                result = OCRResult.from_dict(result_data)
                result.access_count += 1
                # Promote to memory cache
                self.memory_cache.set(cache_key, result.to_dict(),
                                    self._get_cache_ttl(result.confidence))
                return result

        # Try file cache
        if self.file_cache:
            result_data = self.file_cache.get(cache_key)
            if result_data:
                result = OCRResult.from_dict(result_data)
                result.access_count += 1
                # Promote to memory cache
                self.memory_cache.set(cache_key, result.to_dict(),
                                    self._get_cache_ttl(result.confidence))
                return result

        return None

    def cache_plate_text(self, plate_text: str, confidence: float, metadata: Dict = None) -> bool:
        """Cache license plate text with metadata."""
        if confidence < self.confidence_threshold:
            return False

        cache_key = f"{self.PLATE_PREFIX}{plate_text.upper()}"
        ttl = self._get_cache_ttl(confidence)

        cache_data = {
            'text': plate_text,
            'confidence': confidence,
            'metadata': metadata or {},
            'timestamp': time.time()
        }

        # Cache in memory
        success = self.memory_cache.set(cache_key, cache_data, ttl)

        # Cache in Redis if available
        if self.redis_cache and self.redis_cache.is_connected():
            self.redis_cache.set(cache_key, cache_data, ttl)

        return success

    def get_similar_plates(self, plate_text: str) -> List[Dict]:
        """Get similar cached plates."""
        similar_plates = []
        target_text = plate_text.upper()

        # Search memory cache
        for key in self.memory_cache.keys():
            if key.startswith(self.PLATE_PREFIX):
                plate_data = self.memory_cache.get(key)
                if plate_data:
                    cached_text = plate_data['text'].upper()
                    similarity = self._calculate_similarity(target_text, cached_text)
                    if similarity >= self.similarity_threshold:
                        similar_plates.append({
                            **plate_data,
                            'similarity': similarity
                        })

        return sorted(similar_plates, key=lambda x: x['similarity'], reverse=True)

    def cache_image_preprocessing(self, image_data, processed_data: Any) -> bool:
        """Cache image preprocessing results."""
        image_hash = self._generate_image_hash(image_data)
        cache_key = f"{self.IMAGE_PREFIX}{image_hash}"

        # Use shorter TTL for preprocessing results
        ttl = 600  # 10 minutes

        return self.memory_cache.set(cache_key, processed_data, ttl)

    def get_image_preprocessing(self, image_data) -> Optional[Any]:
        """Get cached image preprocessing result."""
        image_hash = self._generate_image_hash(image_data)
        cache_key = f"{self.IMAGE_PREFIX}{image_hash}"

        return self.memory_cache.get(cache_key)

    def invalidate_plate_cache(self, plate_text: str):
        """Invalidate cache entries for a specific plate."""
        cache_key = f"{self.PLATE_PREFIX}{plate_text.upper()}"

        self.memory_cache.delete(cache_key)
        if self.redis_cache:
            self.redis_cache.delete(cache_key)

    def clear_expired_entries(self):
        """Clear expired entries from all caches."""
        # Memory cache handles this automatically
        # Redis handles TTL automatically
        # File cache has background cleanup
        pass

    def get_cache_stats(self) -> Dict:
        """Get comprehensive cache statistics."""
        stats = {
            'memory': self.memory_cache.get_stats(),
            'file': self.file_cache.get_stats() if self.file_cache else None,
            'redis': None
        }

        if self.redis_cache:
            stats['redis'] = {
                'connected': self.redis_cache.is_connected(),
                'size': self.redis_cache.size(),
                'metrics': self.redis_cache.get_metrics()
            }

        return stats

    def warmup_cache(self, common_plates: List[str]):
        """Warm up cache with commonly seen plates."""
        for plate in common_plates:
            self.cache_plate_text(plate, 0.9, {'source': 'warmup'})