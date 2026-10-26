#!/usr/bin/env python3
# SecScan AI core module
"""
Cache Management System for SecScan AI
Provides multi-layer caching with Redis and memory backends
"""

import os
import json
import time
import hashlib
import logging
import threading
import pickle
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import weakref

try:
    import redis
    from redis.sentinel import Sentinel

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available. Install with: pip install redis")

try:
    import memcache

    MEMCACHED_AVAILABLE = True
except ImportError:
    MEMCACHED_AVAILABLE = False
    logging.warning(
        "Memcached not available. Install with: pip install python-memcached"
    )


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    memory_usage: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0

    def is_expired(self) -> bool:
        return self.expires_at and datetime.utcnow() > self.expires_at

    def touch(self):
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


class CacheBackend(ABC):
    """Abstract base class for cache backends"""

    @abstractmethod
    def get(self, key: str) -> Any:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def clear(self) -> bool:
        pass

    @abstractmethod
    def get_stats(self) -> CacheStats:
        pass


class MemoryCache(CacheBackend):
    """In-memory cache backend with LRU eviction"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_expired, daemon=True
        )
        self.cleanup_thread.start()

    def get(self, key: str) -> Any:
        with self.lock:
            if key not in self.cache:
                self.stats.misses += 1
                return None

            entry = self.cache[key]

            if entry.is_expired():
                del self.cache[key]
                self.stats.misses += 1
                self.stats.evictions += 1
                return None

            entry.touch()
            self.stats.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            with self.lock:
                # Calculate expiry time
                expires_at = None
                if ttl is not None:
                    expires_at = datetime.utcnow() + timedelta(seconds=ttl)
                elif self.default_ttl > 0:
                    expires_at = datetime.utcnow() + timedelta(seconds=self.default_ttl)

                # Calculate size
                size_bytes = len(pickle.dumps(value))

                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.utcnow(),
                    expires_at=expires_at,
                    size_bytes=size_bytes,
                )

                # Evict if necessary
                if key not in self.cache and len(self.cache) >= self.max_size:
                    self._evict_lru()

                self.cache[key] = entry
                self.stats.sets += 1
                self.stats.memory_usage += size_bytes

                return True

        except Exception as e:
            self.logger.error(f"Error setting cache key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                del self.cache[key]
                self.stats.deletes += 1
                self.stats.memory_usage -= entry.size_bytes
                return True
            return False

    def exists(self, key: str) -> bool:
        with self.lock:
            return key in self.cache and not self.cache[key].is_expired()

    def clear(self) -> bool:
        with self.lock:
            self.cache.clear()
            self.stats = CacheStats()
            return True

    def get_stats(self) -> CacheStats:
        with self.lock:
            return self.stats

    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self.cache:
            return

        # Find LRU entry
        lru_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].last_accessed or self.cache[k].created_at,
        )

        entry = self.cache[lru_key]
        del self.cache[lru_key]
        self.stats.evictions += 1
        self.stats.memory_usage -= entry.size_bytes

        self.logger.debug(f"Evicted LRU cache entry: {lru_key}")

    def _cleanup_expired(self):
        """Background cleanup of expired entries"""
        while True:
            try:
                with self.lock:
                    expired_keys = [
                        key for key, entry in self.cache.items() if entry.is_expired()
                    ]

                    for key in expired_keys:
                        entry = self.cache[key]
                        del self.cache[key]
                        self.stats.evictions += 1
                        self.stats.memory_usage -= entry.size_bytes

                if expired_keys:
                    self.logger.debug(
                        f"Cleaned up {len(expired_keys)} expired cache entries"
                    )

                time.sleep(60)  # Cleanup every minute

            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")
                time.sleep(60)


class RedisCache(CacheBackend):
    """Redis cache backend"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "secscan_ai:",
        default_ttl: int = 3600,
        sentinel_hosts: Optional[List[tuple]] = None,
        sentinel_service: str = "mymaster",
    ):

        self.prefix = prefix
        self.default_ttl = default_ttl
        self.logger = logging.getLogger(__name__)
        self.stats = CacheStats()

        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis not available. Install with: pip install redis")

        try:
            if sentinel_hosts:
                # Redis Sentinel for high availability
                sentinel = Sentinel(sentinel_hosts)
                self.client = sentinel.master_for(
                    sentinel_service, socket_timeout=0.1, password=password, db=db
                )
            else:
                # Direct Redis connection
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=False,  # We'll handle encoding
                )

            # Test connection
            self.client.ping()
            self.logger.info(f"Redis cache connected to {host}:{port}")

        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _make_key(self, key: str) -> str:
        """Add prefix to key"""
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Any:
        try:
            redis_key = self._make_key(key)
            data = self.client.get(redis_key)

            if data is None:
                self.stats.misses += 1
                return None

            value = pickle.loads(data)
            self.stats.hits += 1
            return value

        except Exception as e:
            self.logger.error(f"Error getting key {key} from Redis: {e}")
            self.stats.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            redis_key = self._make_key(key)
            data = pickle.dumps(value)

            if ttl is not None:
                result = self.client.setex(redis_key, ttl, data)
            elif self.default_ttl > 0:
                result = self.client.setex(redis_key, self.default_ttl, data)
            else:
                result = self.client.set(redis_key, data)

            if result:
                self.stats.sets += 1
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error setting key {key} in Redis: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            redis_key = self._make_key(key)
            result = self.client.delete(redis_key)

            if result:
                self.stats.deletes += 1
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error deleting key {key} from Redis: {e}")
            return False

    def exists(self, key: str) -> bool:
        try:
            redis_key = self._make_key(key)
            return bool(self.client.exists(redis_key))
        except Exception as e:
            self.logger.error(f"Error checking existence of key {key} in Redis: {e}")
            return False

    def clear(self) -> bool:
        try:
            # Delete all keys with our prefix
            keys = self.client.keys(f"{self.prefix}*")
            if keys:
                self.client.delete(*keys)
            return True
        except Exception as e:
            self.logger.error(f"Error clearing Redis cache: {e}")
            return False

    def get_stats(self) -> CacheStats:
        return self.stats


class CacheManager:
    """Multi-layer cache manager with L1 (memory) and L2 (Redis) caches"""

    def __init__(
        self,
        l1_cache: Optional[CacheBackend] = None,
        l2_cache: Optional[CacheBackend] = None,
        l1_ttl: int = 300,  # 5 minutes
        l2_ttl: int = 3600,
    ):  # 1 hour

        self.l1_cache = l1_cache or MemoryCache(max_size=1000, default_ttl=l1_ttl)
        self.l2_cache = l2_cache
        self.l1_ttl = l1_ttl
        self.l2_ttl = l2_ttl
        self.logger = logging.getLogger(__name__)

        # Cache for function decorators
        self.function_cache = weakref.WeakKeyDictionary()

    def get(self, key: str) -> Any:
        """Get value from cache (L1 first, then L2)"""
        # Try L1 cache first
        value = self.l1_cache.get(key)
        if value is not None:
            return value

        # Try L2 cache
        if self.l2_cache:
            value = self.l2_cache.get(key)
            if value is not None:
                # Populate L1 cache
                self.l1_cache.set(key, value, self.l1_ttl)
                return value

        return None

    def set(
        self,
        key: str,
        value: Any,
        l1_ttl: Optional[int] = None,
        l2_ttl: Optional[int] = None,
    ) -> bool:
        """Set value in both cache layers"""
        l1_success = self.l1_cache.set(key, value, l1_ttl or self.l1_ttl)

        l2_success = True
        if self.l2_cache:
            l2_success = self.l2_cache.set(key, value, l2_ttl or self.l2_ttl)

        return l1_success and l2_success

    def delete(self, key: str) -> bool:
        """Delete from both cache layers"""
        l1_success = self.l1_cache.delete(key)

        l2_success = True
        if self.l2_cache:
            l2_success = self.l2_cache.delete(key)

        return l1_success and l2_success

    def exists(self, key: str) -> bool:
        """Check if key exists in any cache layer"""
        return self.l1_cache.exists(key) or (
            self.l2_cache and self.l2_cache.exists(key)
        )

    def clear(self) -> bool:
        """Clear both cache layers"""
        l1_success = self.l1_cache.clear()

        l2_success = True
        if self.l2_cache:
            l2_success = self.l2_cache.clear()

        return l1_success and l2_success

    def get_stats(self) -> Dict[str, CacheStats]:
        """Get statistics for all cache layers"""
        stats = {"l1": self.l1_cache.get_stats()}

        if self.l2_cache:
            stats["l2"] = self.l2_cache.get_stats()

        return stats

    def cache_result(
        self, ttl: Optional[int] = None, key_func: Optional[Callable] = None
    ):
        """Decorator for caching function results"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self._generate_cache_key(func, args, kwargs)

                # Try to get from cache
                result = self.get(cache_key)
                if result is not None:
                    return result

                # Execute function
                result = func(*args, **kwargs)

                # Cache result
                self.set(cache_key, result, ttl)

                return result

            return wrapper

        return decorator

    def memoize(self, ttl: Optional[int] = None):
        """Decorator for memoizing function results"""

        def decorator(func):
            cache_key = f"memoize:{func.__module__}.{func.__name__}"

            if func not in self.function_cache:
                self.function_cache[func] = {}

            def wrapper(*args, **kwargs):
                # Generate argument hash
                arg_key = self._hash_args(args, kwargs)
                full_key = f"{cache_key}:{arg_key}"

                # Try cache first
                result = self.get(full_key)
                if result is not None:
                    return result

                # Execute function
                result = func(*args, **kwargs)

                # Cache result
                self.set(full_key, result, ttl)

                return result

            return wrapper

        return decorator

    def _generate_cache_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Generate cache key for function call"""
        func_name = f"{func.__module__}.{func.__name__}"
        arg_hash = self._hash_args(args, kwargs)
        return f"cache:{func_name}:{arg_hash}"

    def _hash_args(self, args: tuple, kwargs: dict) -> str:
        """Generate hash for function arguments"""
        try:
            # Create a stable representation of arguments
            arg_data = {"args": args, "kwargs": sorted(kwargs.items())}

            arg_str = json.dumps(arg_data, sort_keys=True, default=str)
            return hashlib.md5(arg_str.encode()).hexdigest()[:16]

        except Exception:
            # Fallback to simple hash
            return hashlib.md5(str((args, kwargs)).encode()).hexdigest()[:16]

    def warm_up(self, warm_up_data: Dict[str, Any]):
        """Pre-populate cache with data"""
        for key, value in warm_up_data.items():
            self.set(key, value)

        self.logger.info(f"Cache warmed up with {len(warm_up_data)} entries")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get comprehensive cache information"""
        stats = self.get_stats()

        info = {
            "layers": len(stats),
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add L1 specific info
        if isinstance(self.l1_cache, MemoryCache):
            with self.l1_cache.lock:
                info["l1_entries"] = len(self.l1_cache.cache)
                info["l1_max_size"] = self.l1_cache.max_size

        # Add L2 specific info
        if self.l2_cache and isinstance(self.l2_cache, RedisCache):
            try:
                redis_info = self.l2_cache.client.info()
                info["l2_redis_info"] = {
                    "used_memory": redis_info.get("used_memory"),
                    "connected_clients": redis_info.get("connected_clients"),
                    "keyspace_hits": redis_info.get("keyspace_hits"),
                    "keyspace_misses": redis_info.get("keyspace_misses"),
                }
            except Exception:
                pass

        return info


# Singleton cache manager
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager

    if _cache_manager is None:
        # Initialize with default configuration
        l1_cache = MemoryCache(max_size=1000, default_ttl=300)

        # Try to initialize Redis L2 cache
        l2_cache = None
        if REDIS_AVAILABLE:
            try:
                redis_host = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))
                redis_password = os.getenv("REDIS_PASSWORD")

                l2_cache = RedisCache(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    prefix="secscan_ai:cache:",
                )
            except Exception:
                pass  # Fall back to L1 only

        _cache_manager = CacheManager(l1_cache=l1_cache, l2_cache=l2_cache)

    return _cache_manager
