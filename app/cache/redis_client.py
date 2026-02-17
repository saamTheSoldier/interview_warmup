"""
Redis client - caching and related use cases (job requirement).
Challenge: Connection pooling, fail gracefully when Redis is down.
Design: Single client instance, dependency injection for testability.
"""

import json
from typing import Any

from redis.asyncio import Redis

from app.config import get_settings

settings = get_settings()

# Shared async Redis client (connection pool managed by redis-py)
_redis: Redis | None = None


async def get_redis() -> Redis:
    """Get Redis connection. Used as FastAPI dependency."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def cache_get(key: str) -> str | None:
    """Get value from cache. Returns None if miss or error (graceful degradation)."""
    try:
        client = await get_redis()
        return await client.get(key)
    except Exception:
        return None


async def cache_set(key: str, value: str | dict[str, Any], ttl_seconds: int = 300) -> bool:
    """Set value in cache with TTL. Dict is JSON-serialized."""
    try:
        client = await get_redis()
        if isinstance(value, dict):
            value = json.dumps(value)
        await client.setex(key, ttl_seconds, value)
        return True
    except Exception:
        return False


async def cache_delete(key: str) -> bool:
    """Invalidate cache key (e.g. after item update)."""
    try:
        client = await get_redis()
        await client.delete(key)
        return True
    except Exception:
        return False
