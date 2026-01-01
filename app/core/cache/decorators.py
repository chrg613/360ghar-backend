"""
Caching decorators for FastAPI endpoints and service functions.
"""

import functools
from typing import Any, Awaitable, Callable, List, Optional, TypeVar, Union

from fastapi import Request

from app.core.cache.keys import build_cache_key, generate_hash
from app.core.logging import get_logger

logger = get_logger(__name__)

# Type variable for return types
T = TypeVar("T")


def cached(
    prefix: str,
    ttl: int = 300,
    key_params: Optional[List[str]] = None,
    include_user: bool = False,
    cache_none: bool = False,
    condition: Optional[Callable[..., bool]] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator for caching async function results.

    Args:
        prefix: Cache key prefix
        ttl: Time-to-live in seconds
        key_params: Specific kwargs to include in key (None = all serializable)
        include_user: Include current_user in cache key
        cache_none: Whether to cache None results
        condition: Optional callable to determine if result should be cached

    Usage:
        @cached("amenities", ttl=86400)
        async def get_all_amenities(db: AsyncSession):
            ...

        @cached("properties", ttl=300, key_params=["city", "purpose"])
        async def search_properties(db: AsyncSession, city: str, purpose: str):
            ...
    """

    def decorator(
        func: Callable[..., Awaitable[T]],
    ) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Import here to avoid circular imports
            from app.core.cache import get_cache_manager

            cache = get_cache_manager()

            if not cache.is_available():
                return await func(*args, **kwargs)

            # Build cache key
            user_id = None
            if include_user and "current_user" in kwargs:
                user = kwargs.get("current_user")
                user_id = getattr(user, "id", None) if user else None

            # Extract relevant kwargs for key
            if key_params:
                key_kwargs = {k: kwargs.get(k) for k in key_params}
            else:
                # Exclude non-serializable objects
                key_kwargs = {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ("db", "current_user", "request", "session")
                }

            cache_key = build_cache_key(
                prefix,
                include_user=include_user,
                user_id=user_id,
                **key_kwargs,
            )

            # Try cache
            try:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value
            except Exception as e:
                logger.warning(f"Cache get error: {e}")

            # Execute function
            result = await func(*args, **kwargs)

            # Check caching condition
            should_cache = True
            if result is None and not cache_none:
                should_cache = False
            if condition and not condition(result):
                should_cache = False

            # Store in cache
            if should_cache:
                try:
                    # Serialize Pydantic models
                    cache_value = _serialize_for_cache(result)
                    await cache.set(cache_key, cache_value, ttl)
                    logger.debug(f"Cache set: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache set error: {e}")

            return result

        return wrapper

    return decorator


def cache_response(
    prefix: str,
    ttl: int = 300,
    key_builder: Optional[Callable[[Request], str]] = None,
    vary_by_user: bool = False,
) -> Callable:
    """Decorator specifically for FastAPI endpoint responses.

    This decorator works with the Request object to build cache keys
    from query parameters automatically.

    Args:
        prefix: Cache key prefix
        ttl: TTL in seconds
        key_builder: Custom key builder function
        vary_by_user: Whether to vary cache by authenticated user

    Usage:
        @router.get("/amenities/")
        @cache_response("amenities", ttl=86400)
        async def list_amenities(db: AsyncSession = Depends(get_db)):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from app.core.cache import get_cache_manager

            cache = get_cache_manager()

            if not cache.is_available():
                return await func(*args, **kwargs)

            # Try to find Request in args/kwargs
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            # Build cache key
            if key_builder and request:
                cache_key = key_builder(request)
            elif request:
                user_id = None
                if vary_by_user:
                    current_user = kwargs.get("current_user")
                    user_id = (
                        getattr(current_user, "id", None) if current_user else None
                    )

                params_hash = generate_hash(dict(request.query_params))
                cache_key = build_cache_key(
                    prefix,
                    request.url.path,
                    params_hash,
                    include_user=vary_by_user,
                    user_id=user_id,
                )
            else:
                # Fallback: hash relevant kwargs
                key_kwargs = {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ("db", "current_user", "request", "session")
                }
                cache_key = build_cache_key(prefix, generate_hash(key_kwargs))

            # Try cache
            try:
                cached = await cache.get(cache_key)
                if cached is not None:
                    logger.debug(f"Response cache hit: {cache_key}")
                    return cached
            except Exception as e:
                logger.warning(f"Response cache get error: {e}")

            # Execute endpoint
            result = await func(*args, **kwargs)

            # Cache result
            try:
                cache_value = _serialize_for_cache(result)
                await cache.set(cache_key, cache_value, ttl)
                logger.debug(f"Response cache set: {cache_key}")
            except Exception as e:
                logger.warning(f"Response cache set error: {e}")

            return result

        return wrapper

    return decorator


def invalidate_cache(patterns: Union[str, List[str]]) -> Callable:
    """Decorator to invalidate cache patterns after function execution.

    Args:
        patterns: Cache key pattern or list of patterns to invalidate

    Usage:
        @invalidate_cache("properties:*")
        @invalidate_cache(["properties:*"])
        async def create_property(...):
            ...
    """

    normalized_patterns = [patterns] if isinstance(patterns, str) else list(patterns)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)

            # Invalidate after successful execution
            from app.core.cache import get_cache_manager

            cache = get_cache_manager()

            for pattern in normalized_patterns:
                try:
                    deleted = await cache.delete_pattern(pattern)
                    if deleted > 0:
                        logger.debug(
                            f"Invalidated {deleted} keys for pattern: {pattern}"
                        )
                except Exception as e:
                    logger.warning(f"Cache invalidation error for {pattern}: {e}")

            return result

        return wrapper

    return decorator


def _serialize_for_cache(value: Any) -> Any:
    """Serialize value for cache storage.

    Handles Pydantic models, lists of models, and dicts.
    """
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    elif isinstance(value, list):
        return [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in value
        ]
    elif isinstance(value, dict):
        return {
            k: _serialize_for_cache(v)
            for k, v in value.items()
        }
    return value
