import json
import redis.asyncio as redis
from functools import wraps
from time import monotonic
from typing import Callable, Optional, Any
from uuid import UUID

from app.core.config import settings
from app.core.logging import logger


class RedisCache:
    """Redis cache client"""

    _client: Optional[redis.Redis] = None
    _disabled_until: float = 0.0
    _failure_backoff_seconds: float = 30.0

    @classmethod
    async def get_client(cls) -> Optional[redis.Redis]:
        """Get Redis client instance"""
        if monotonic() < cls._disabled_until:
            return None

        if cls._client is None and settings.REDIS_URL:
            try:
                cls._client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=0.2,
                    socket_timeout=0.2,
                )
                # Test connection
                await cls._client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                if cls._client:
                    await cls._client.aclose()
                cls._client = None
                cls._disabled_until = monotonic() + cls._failure_backoff_seconds
        return cls._client

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection"""
        if cls._client:
            await cls._client.aclose()
            cls._client = None
            cls._disabled_until = 0.0
            logger.info("Redis connection closed")

    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        """Get value from cache"""
        client = await cls.get_client()
        if not client:
            return None

        try:
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None

    @classmethod
    async def set(cls, key: str, value: Any, ttl: int = 300) -> None:
        """Set value to cache with TTL (seconds)"""
        client = await cls.get_client()
        if not client:
            return

        try:
            await client.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")

    @classmethod
    async def delete(cls, key: str) -> None:
        """Delete value from cache"""
        client = await cls.get_client()
        if not client:
            return

        try:
            await client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")

    @classmethod
    async def delete_pattern(cls, pattern: str) -> None:
        """Delete all keys matching pattern"""
        client = await cls.get_client()
        if not client:
            return

        try:
            keys = await client.keys(pattern)
            if keys:
                await client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis delete pattern failed: {e}")


def cache_result(ttl: int = 300, key_prefix: Optional[str] = None):
    """
    Decorator to cache function results

    Args:
        ttl: Time to live in seconds
        key_prefix: Optional prefix for cache key, defaults to function name
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or func.__name__

            # Convert args and kwargs to string representations
            args_str = ":".join(str(arg) for arg in args if isinstance(arg, (str, int, UUID)))
            kwargs_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if isinstance(v, (str, int, UUID)))

            key_parts = [prefix]
            if args_str:
                key_parts.append(args_str)
            if kwargs_str:
                key_parts.append(kwargs_str)

            cache_key = ":".join(key_parts)

            # Try to get from cache first
            cached_result = await RedisCache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_result

            # Call the function
            result = await func(*args, **kwargs)

            # Store in cache
            await RedisCache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


# Cache key templates
CACHE_KEYS = {
    "event_stats": "event:{event_id}:stats",
    "team_templates": "team:{team_id}:templates",
    "photo_metadata": "photo:{photo_id}:metadata",
    "event_photos": "event:{event_id}:photos:{skip}:{limit}",
    "printer_status": "printer:{printer_id}:status",
}
