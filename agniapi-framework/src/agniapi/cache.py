"""
Caching system for AgniAPI with multiple backend support.

This module provides comprehensive caching capabilities including:
- Multiple backends: Redis, Memory, File-based
- Cache decorators for functions and methods
- Cache invalidation and management
- Async and sync support
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import pickle
import time
from abc import ABC, abstractmethod
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar
import threading

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

F = TypeVar('F', bound=Callable[..., Any])


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set value in cache with optional timeout."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache. Returns True if key existed."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass


class MemoryCache(CacheBackend):
    """In-memory cache backend using a dictionary."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry['expires'] and time.time() > entry['expires']:
                del self._cache[key]
                return None
            
            return entry['value']
    
    async def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set value in memory cache."""
        with self._lock:
            # Evict oldest entries if at max size
            if len(self._cache) >= self.max_size and key not in self._cache:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            expires = None
            if timeout:
                expires = time.time() + timeout
            
            self._cache[key] = {
                'value': value,
                'expires': expires,
                'created': time.time()
            }
    
    async def delete(self, key: str) -> bool:
        """Delete key from memory cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all entries from memory cache."""
        with self._lock:
            self._cache.clear()
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        value = await self.get(key)
        return value is not None


class RedisCache(CacheBackend):
    """Redis cache backend."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", **kwargs):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis is not available. Install with: pip install redis")
        
        self.redis_url = redis_url
        self.redis_kwargs = kwargs
        self._client: Optional[aioredis.Redis] = None
    
    async def _get_client(self) -> aioredis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = aioredis.from_url(self.redis_url, **self.redis_kwargs)
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        client = await self._get_client()
        data = await client.get(key)
        if data is None:
            return None
        
        try:
            return pickle.loads(data)
        except (pickle.PickleError, TypeError):
            return None
    
    async def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set value in Redis cache."""
        client = await self._get_client()
        data = pickle.dumps(value)
        
        if timeout:
            await client.setex(key, timeout, data)
        else:
            await client.set(key, data)
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache."""
        client = await self._get_client()
        result = await client.delete(key)
        return result > 0
    
    async def clear(self) -> None:
        """Clear all entries from Redis cache."""
        client = await self._get_client()
        await client.flushdb()
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        client = await self._get_client()
        result = await client.exists(key)
        return result > 0


class FileCache(CacheBackend):
    """File-based cache backend."""
    
    def __init__(self, cache_dir: Union[str, Path] = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._lock = threading.RLock()
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Use hash to avoid filesystem issues with special characters
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from file cache."""
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            # Check if expired
            if data['expires'] and time.time() > data['expires']:
                file_path.unlink(missing_ok=True)
                return None
            
            return data['value']
        except (pickle.PickleError, FileNotFoundError, KeyError):
            return None
    
    async def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set value in file cache."""
        file_path = self._get_file_path(key)
        
        expires = None
        if timeout:
            expires = time.time() + timeout
        
        data = {
            'value': value,
            'expires': expires,
            'created': time.time()
        }
        
        with self._lock:
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
    
    async def delete(self, key: str) -> bool:
        """Delete key from file cache."""
        file_path = self._get_file_path(key)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    async def clear(self) -> None:
        """Clear all entries from file cache."""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink(missing_ok=True)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in file cache."""
        value = await self.get(key)
        return value is not None


class Cache:
    """Main cache interface with decorator support."""
    
    def __init__(self, backend: CacheBackend, key_prefix: str = "agniapi"):
        self.backend = backend
        self.key_prefix = key_prefix
    
    def _make_key(self, key: str) -> str:
        """Create full cache key with prefix."""
        return f"{self.key_prefix}:{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return await self.backend.get(self._make_key(key))
    
    async def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set value in cache."""
        await self.backend.set(self._make_key(key), value, timeout)
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        return await self.backend.delete(self._make_key(key))
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        await self.backend.clear()
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return await self.backend.exists(self._make_key(key))
    
    def _generate_cache_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Generate cache key for function call."""
        # Create a deterministic key from function name and arguments
        func_name = f"{func.__module__}.{func.__qualname__}"
        
        # Convert args and kwargs to a hashable representation
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        
        return f"func:{func_name}:{key_hash}"
    
    def cached(self, timeout: Optional[int] = 300, key_prefix: Optional[str] = None) -> Callable[[F], F]:
        """
        Decorator to cache function results.
        
        Args:
            timeout: Cache timeout in seconds (default: 5 minutes)
            key_prefix: Custom key prefix for this cached function
        """
        def decorator(func: F) -> F:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                cache_key = self._generate_cache_key(func, args, kwargs)
                if key_prefix:
                    cache_key = f"{key_prefix}:{cache_key}"
                
                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Call function and cache result
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                await self.set(cache_key, result, timeout)
                return result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, we need to handle async cache operations
                cache_key = self._generate_cache_key(func, args, kwargs)
                if key_prefix:
                    cache_key = f"{key_prefix}:{cache_key}"
                
                # Try to get from cache (run async in sync context)
                try:
                    loop = asyncio.get_event_loop()
                    cached_result = loop.run_until_complete(self.get(cache_key))
                    if cached_result is not None:
                        return cached_result
                except RuntimeError:
                    # No event loop, skip caching
                    return func(*args, **kwargs)
                
                # Call function and cache result
                result = func(*args, **kwargs)
                
                try:
                    loop.run_until_complete(self.set(cache_key, result, timeout))
                except RuntimeError:
                    # No event loop, skip caching
                    pass
                
                return result
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def memoize(self, timeout: Optional[int] = 300) -> Callable[[F], F]:
        """
        Decorator to memoize function results (alias for cached).
        """
        return self.cached(timeout=timeout)


# Default cache instances
memory_cache = Cache(MemoryCache())
cache = memory_cache  # Default cache instance


def configure_cache(backend_type: str = "memory", **kwargs) -> Cache:
    """
    Configure and return a cache instance.
    
    Args:
        backend_type: Type of cache backend ("memory", "redis", "file")
        **kwargs: Backend-specific configuration
    """
    if backend_type == "memory":
        backend = MemoryCache(**kwargs)
    elif backend_type == "redis":
        backend = RedisCache(**kwargs)
    elif backend_type == "file":
        backend = FileCache(**kwargs)
    else:
        raise ValueError(f"Unknown cache backend: {backend_type}")
    
    return Cache(backend)
