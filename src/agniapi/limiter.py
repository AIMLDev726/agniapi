"""
Rate limiting system for AgniAPI.

This module provides comprehensive rate limiting capabilities including:
- Multiple rate limiting strategies (fixed window, sliding window, token bucket)
- Multiple storage backends (memory, Redis)
- Flexible rate limit definitions
- Decorator support for easy integration
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import threading
import re

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .exceptions import HTTPException


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(status_code=429, detail=detail)
        self.retry_after = retry_after


class RateLimitStorage(ABC):
    """Abstract base class for rate limit storage backends."""
    
    @abstractmethod
    async def get_window_count(self, key: str, window_size: int) -> int:
        """Get the current count for a time window."""
        pass
    
    @abstractmethod
    async def increment_window(self, key: str, window_size: int, increment: int = 1) -> int:
        """Increment the count for a time window and return new count."""
        pass
    
    @abstractmethod
    async def get_sliding_window_count(self, key: str, window_size: int) -> int:
        """Get count for sliding window."""
        pass
    
    @abstractmethod
    async def add_sliding_window_hit(self, key: str, window_size: int) -> int:
        """Add a hit to sliding window and return current count."""
        pass
    
    @abstractmethod
    async def get_token_bucket(self, key: str) -> Tuple[int, float]:
        """Get current token count and last refill time."""
        pass
    
    @abstractmethod
    async def update_token_bucket(self, key: str, tokens: int, last_refill: float) -> None:
        """Update token bucket state."""
        pass


class MemoryRateLimitStorage(RateLimitStorage):
    """In-memory rate limit storage."""
    
    def __init__(self):
        self._windows: Dict[str, Dict[int, int]] = defaultdict(dict)
        self._sliding_windows: Dict[str, deque] = defaultdict(deque)
        self._token_buckets: Dict[str, Tuple[int, float]] = {}
        self._lock = threading.RLock()
    
    async def get_window_count(self, key: str, window_size: int) -> int:
        """Get the current count for a time window."""
        with self._lock:
            current_window = int(time.time()) // window_size
            return self._windows[key].get(current_window, 0)
    
    async def increment_window(self, key: str, window_size: int, increment: int = 1) -> int:
        """Increment the count for a time window and return new count."""
        with self._lock:
            current_window = int(time.time()) // window_size
            
            # Clean old windows
            windows_to_remove = []
            for window_time in self._windows[key]:
                if window_time < current_window - 1:  # Keep current and previous window
                    windows_to_remove.append(window_time)
            
            for window_time in windows_to_remove:
                del self._windows[key][window_time]
            
            # Increment current window
            self._windows[key][current_window] = self._windows[key].get(current_window, 0) + increment
            return self._windows[key][current_window]
    
    async def get_sliding_window_count(self, key: str, window_size: int) -> int:
        """Get count for sliding window."""
        with self._lock:
            current_time = time.time()
            window_start = current_time - window_size
            
            # Clean old entries
            while self._sliding_windows[key] and self._sliding_windows[key][0] < window_start:
                self._sliding_windows[key].popleft()
            
            return len(self._sliding_windows[key])
    
    async def add_sliding_window_hit(self, key: str, window_size: int) -> int:
        """Add a hit to sliding window and return current count."""
        with self._lock:
            current_time = time.time()
            window_start = current_time - window_size
            
            # Clean old entries
            while self._sliding_windows[key] and self._sliding_windows[key][0] < window_start:
                self._sliding_windows[key].popleft()
            
            # Add new hit
            self._sliding_windows[key].append(current_time)
            return len(self._sliding_windows[key])
    
    async def get_token_bucket(self, key: str) -> Tuple[int, float]:
        """Get current token count and last refill time."""
        with self._lock:
            return self._token_buckets.get(key, (0, time.time()))
    
    async def update_token_bucket(self, key: str, tokens: int, last_refill: float) -> None:
        """Update token bucket state."""
        with self._lock:
            self._token_buckets[key] = (tokens, last_refill)


class RedisRateLimitStorage(RateLimitStorage):
    """Redis-based rate limit storage."""
    
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
    
    async def get_window_count(self, key: str, window_size: int) -> int:
        """Get the current count for a time window."""
        client = await self._get_client()
        current_window = int(time.time()) // window_size
        window_key = f"{key}:window:{current_window}"
        
        count = await client.get(window_key)
        return int(count) if count else 0
    
    async def increment_window(self, key: str, window_size: int, increment: int = 1) -> int:
        """Increment the count for a time window and return new count."""
        client = await self._get_client()
        current_window = int(time.time()) // window_size
        window_key = f"{key}:window:{current_window}"
        
        # Use pipeline for atomic operations
        pipe = client.pipeline()
        pipe.incr(window_key, increment)
        pipe.expire(window_key, window_size * 2)  # Expire after 2 windows
        results = await pipe.execute()
        
        return results[0]
    
    async def get_sliding_window_count(self, key: str, window_size: int) -> int:
        """Get count for sliding window."""
        client = await self._get_client()
        current_time = time.time()
        window_start = current_time - window_size
        
        # Use sorted set to store timestamps
        sliding_key = f"{key}:sliding"
        
        # Remove old entries and count current ones
        pipe = client.pipeline()
        pipe.zremrangebyscore(sliding_key, 0, window_start)
        pipe.zcard(sliding_key)
        results = await pipe.execute()
        
        return results[1]
    
    async def add_sliding_window_hit(self, key: str, window_size: int) -> int:
        """Add a hit to sliding window and return current count."""
        client = await self._get_client()
        current_time = time.time()
        window_start = current_time - window_size
        
        sliding_key = f"{key}:sliding"
        
        # Add current hit and clean old entries
        pipe = client.pipeline()
        pipe.zadd(sliding_key, {str(current_time): current_time})
        pipe.zremrangebyscore(sliding_key, 0, window_start)
        pipe.zcard(sliding_key)
        pipe.expire(sliding_key, window_size + 60)  # Expire with buffer
        results = await pipe.execute()
        
        return results[2]
    
    async def get_token_bucket(self, key: str) -> Tuple[int, float]:
        """Get current token count and last refill time."""
        client = await self._get_client()
        bucket_key = f"{key}:bucket"
        
        data = await client.hmget(bucket_key, "tokens", "last_refill")
        tokens = int(data[0]) if data[0] else 0
        last_refill = float(data[1]) if data[1] else time.time()
        
        return tokens, last_refill
    
    async def update_token_bucket(self, key: str, tokens: int, last_refill: float) -> None:
        """Update token bucket state."""
        client = await self._get_client()
        bucket_key = f"{key}:bucket"
        
        await client.hmset(bucket_key, {
            "tokens": tokens,
            "last_refill": last_refill
        })
        await client.expire(bucket_key, 3600)  # Expire after 1 hour of inactivity


class RateLimit:
    """Rate limit definition."""
    
    def __init__(self, limit: int, window: int, strategy: str = "fixed_window"):
        self.limit = limit
        self.window = window
        self.strategy = strategy
    
    @classmethod
    def parse(cls, rate_string: str) -> 'RateLimit':
        """
        Parse rate limit string like "100/hour", "10/minute", "1000/day".
        """
        pattern = r'(\d+)/(\w+)'
        match = re.match(pattern, rate_string.strip())
        
        if not match:
            raise ValueError(f"Invalid rate limit format: {rate_string}")
        
        limit = int(match.group(1))
        period = match.group(2).lower()
        
        # Convert period to seconds
        period_map = {
            'second': 1,
            'minute': 60,
            'hour': 3600,
            'day': 86400,
        }
        
        # Handle plurals
        if period.endswith('s'):
            period = period[:-1]
        
        if period not in period_map:
            raise ValueError(f"Unknown time period: {period}")
        
        window = period_map[period]
        return cls(limit, window)


class RateLimiter:
    """Main rate limiter class."""
    
    def __init__(
        self,
        storage: Optional[RateLimitStorage] = None,
        default_limits: Optional[List[str]] = None,
        key_func: Optional[Callable] = None,
    ):
        self.storage = storage or MemoryRateLimitStorage()
        self.default_limits = [RateLimit.parse(limit) for limit in (default_limits or [])]
        self.key_func = key_func or self._default_key_func
        self._route_limits: Dict[str, List[RateLimit]] = {}
    
    def _default_key_func(self) -> str:
        """Default key function that uses client IP."""
        # This will be overridden by the application to get actual client IP
        return "default"
    
    async def check_rate_limit(self, key: str, limits: List[RateLimit]) -> None:
        """Check if rate limits are exceeded for a key."""
        for rate_limit in limits:
            if rate_limit.strategy == "fixed_window":
                count = await self._check_fixed_window(key, rate_limit)
            elif rate_limit.strategy == "sliding_window":
                count = await self._check_sliding_window(key, rate_limit)
            elif rate_limit.strategy == "token_bucket":
                count = await self._check_token_bucket(key, rate_limit)
            else:
                raise ValueError(f"Unknown rate limit strategy: {rate_limit.strategy}")
            
            if count > rate_limit.limit:
                raise RateLimitExceeded(
                    detail=f"Rate limit exceeded: {rate_limit.limit}/{rate_limit.window}s",
                    retry_after=rate_limit.window
                )
    
    async def _check_fixed_window(self, key: str, rate_limit: RateLimit) -> int:
        """Check fixed window rate limit."""
        window_key = f"{key}:fixed:{rate_limit.window}"
        return await self.storage.increment_window(window_key, rate_limit.window)
    
    async def _check_sliding_window(self, key: str, rate_limit: RateLimit) -> int:
        """Check sliding window rate limit."""
        window_key = f"{key}:sliding:{rate_limit.window}"
        return await self.storage.add_sliding_window_hit(window_key, rate_limit.window)
    
    async def _check_token_bucket(self, key: str, rate_limit: RateLimit) -> int:
        """Check token bucket rate limit."""
        bucket_key = f"{key}:bucket:{rate_limit.limit}:{rate_limit.window}"
        
        tokens, last_refill = await self.storage.get_token_bucket(bucket_key)
        current_time = time.time()
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = current_time - last_refill
        tokens_to_add = int(time_elapsed * (rate_limit.limit / rate_limit.window))
        
        # Update token count (cap at limit)
        tokens = min(rate_limit.limit, tokens + tokens_to_add)
        
        # Consume one token
        if tokens > 0:
            tokens -= 1
            await self.storage.update_token_bucket(bucket_key, tokens, current_time)
            return rate_limit.limit - tokens  # Return "used" count
        else:
            return rate_limit.limit + 1  # Exceed limit
    
    def limit(self, rate_string: str, key_func: Optional[Callable] = None) -> Callable:
        """Decorator to apply rate limiting to a function."""
        rate_limit = RateLimit.parse(rate_string)
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Get rate limit key
                if key_func:
                    key = key_func()
                else:
                    key = self.key_func()
                
                # Check rate limit
                await self.check_rate_limit(key, [rate_limit])
                
                # Call original function
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, we need to handle async rate limiting
                try:
                    loop = asyncio.get_event_loop()
                    
                    # Get rate limit key
                    if key_func:
                        key = key_func()
                    else:
                        key = self.key_func()
                    
                    # Check rate limit
                    loop.run_until_complete(self.check_rate_limit(key, [rate_limit]))
                    
                except RuntimeError:
                    # No event loop, skip rate limiting
                    pass
                
                return func(*args, **kwargs)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator


# Default limiter instance
limiter = RateLimiter()


def configure_limiter(
    storage_type: str = "memory",
    default_limits: Optional[List[str]] = None,
    key_func: Optional[Callable] = None,
    **kwargs
) -> RateLimiter:
    """Configure and return a rate limiter instance."""
    if storage_type == "memory":
        storage = MemoryRateLimitStorage()
    elif storage_type == "redis":
        storage = RedisRateLimitStorage(**kwargs)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
    
    return RateLimiter(storage=storage, default_limits=default_limits, key_func=key_func)
