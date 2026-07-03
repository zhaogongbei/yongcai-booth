"""
Redis cache decorators for repository methods.

Provides transparent caching layer for repository queries with:
- Automatic cache key generation
- TTL-based expiration
- Cache invalidation support
- Graceful fallback when Redis unavailable
"""

import json
import logging
from functools import wraps
from typing import Any, Callable, List, Optional
from uuid import UUID

from app.core.cache import RedisCache

logger = logging.getLogger(__name__)


def cached(
    ttl: int = 300, key_prefix: Optional[str] = None, key_builder: Optional[Callable] = None
):
    """
    Cache decorator for repository methods with Redis.

    Automatically caches method results using Redis with configurable TTL.
    Falls back to direct DB query if Redis is unavailable.

    Args:
        ttl: Time to live in seconds (default: 300 = 5 minutes)
        key_prefix: Optional prefix for cache key (defaults to method name)
        key_builder: Custom function to build cache key from args/kwargs

    Returns:
        Decorator function

    Example:
        @cached(ttl=600, key_prefix="user")
        async def get_by_email(self, email: str) -> Optional[User]:
            # Query implementation
            pass

        @cached(ttl=300, key_builder=lambda self, team_id, skip, limit: f"team:{team_id}:events:{skip}:{limit}")
        async def get_by_team(self, team_id: UUID, skip: int = 0, limit: int = 100):
            # Query implementation
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Build cache key
            if key_builder:
                try:
                    cache_key = key_builder(self, *args, **kwargs)
                except Exception as e:
                    logger.warning(f"Custom key_builder failed: {e}, using default")
                    cache_key = _build_default_cache_key(func, key_prefix, args, kwargs)
            else:
                cache_key = _build_default_cache_key(func, key_prefix, args, kwargs)

            # Try to get from cache
            cached_result = await RedisCache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return _deserialize_result(cached_result, func)

            # Cache miss - execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(self, *args, **kwargs)

            # Store in cache (async, don't block on failure)
            try:
                serialized = _serialize_result(result)
                await RedisCache.set(cache_key, serialized, ttl)
            except Exception as e:
                logger.warning(f"Failed to cache result for {cache_key}: {e}")

            return result

        return wrapper

    return decorator


def invalidate_cache(key_pattern: str):
    """
    Decorator to invalidate cache after mutation operations.

    Use this decorator on create/update/delete methods to automatically
    clear related cached queries.

    Args:
        key_pattern: Redis key pattern to delete (supports wildcards)

    Returns:
        Decorator function

    Example:
        @invalidate_cache("team:*:events:*")
        async def create(self, obj_in: dict) -> Event:
            # Create event
            return event

        @invalidate_cache("user:{self.args[0]}:*")
        async def update(self, user_id: UUID, obj_in: dict) -> User:
            # Update user
            return user
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Execute the mutation
            result = await func(self, *args, **kwargs)

            # Invalidate cache (async, don't block on failure)
            try:
                # Support dynamic pattern with args/kwargs
                pattern = key_pattern
                if "{self.args[0]}" in pattern and args:
                    pattern = pattern.replace("{self.args[0]}", str(args[0]))

                await RedisCache.delete_pattern(pattern)
                logger.debug(f"Invalidated cache pattern: {pattern}")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache {key_pattern}: {e}")

            return result

        return wrapper

    return decorator


def _build_default_cache_key(
    func: Callable, key_prefix: Optional[str], args: tuple, kwargs: dict
) -> str:
    """
    Build default cache key from function name and arguments.

    Args:
        func: The function being cached
        key_prefix: Optional prefix override
        args: Positional arguments (excluding self)
        kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    prefix = key_prefix or func.__name__

    # Convert args to string (skip self)
    args_parts = []
    for arg in args:
        if isinstance(arg, (str, int, UUID)):
            args_parts.append(str(arg))
        elif isinstance(arg, bool):
            args_parts.append(str(arg).lower())

    # Convert kwargs to string
    kwargs_parts = []
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, UUID, bool)):
            kwargs_parts.append(f"{k}={v}")

    # Build final key
    key_components = [prefix]
    if args_parts:
        key_components.extend(args_parts)
    if kwargs_parts:
        key_components.extend(kwargs_parts)

    return ":".join(key_components)


def _serialize_result(result: Any) -> Any:
    """
    Serialize query result for caching.

    Handles:
    - None
    - Single ORM objects -> dict
    - Lists of ORM objects -> list of dicts
    - Primitive types (int, str, bool)

    Args:
        result: Query result to serialize

    Returns:
        JSON-serializable object
    """
    if result is None:
        return None

    if isinstance(result, (int, str, bool, float)):
        return result

    if isinstance(result, list):
        return [_serialize_orm_object(item) for item in result]

    # Single ORM object
    return _serialize_orm_object(result)


def _serialize_orm_object(obj: Any) -> dict:
    """
    Convert SQLAlchemy ORM object to dictionary.

    Args:
        obj: ORM model instance

    Returns:
        Dictionary with column values
    """
    if not hasattr(obj, "__table__"):
        return obj

    result = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        # Convert UUID to string for JSON serialization
        if isinstance(value, UUID):
            result[column.name] = str(value)
        else:
            result[column.name] = value

    return result


def _deserialize_result(cached_data: Any, func: Callable) -> Any:
    """
    Deserialize cached data back to expected type.

    Note: Returns plain dicts/primitives, not ORM objects.
    This is acceptable for read-only operations.

    Args:
        cached_data: Data from cache
        func: Original function (for type hints)

    Returns:
        Deserialized result
    """
    # For now, return cached data as-is (dicts instead of ORM objects)
    # This works fine for read operations
    # If you need full ORM objects with relationships, skip caching
    return cached_data


# Pre-defined cache key patterns for common invalidation scenarios
CACHE_PATTERNS = {
    "event_all": "event:*",
    "event_by_id": "event:{event_id}:*",
    "team_events": "team:{team_id}:events:*",
    "photo_all": "photo:*",
    "photo_by_event": "event:{event_id}:photos:*",
    "user_teams": "user:{user_id}:teams:*",
    "team_members": "team:{team_id}:members:*",
}
