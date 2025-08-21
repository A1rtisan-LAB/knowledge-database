"""Redis service for caching."""

from typing import Optional, Any
import json
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Redis connection pool
redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    global redis_client, redis_pool
    
    if redis_client is None:
        redis_pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=50,
            decode_responses=True
        )
        redis_client = redis.Redis(connection_pool=redis_pool)
    
    return redis_client


async def init_redis():
    """Initialize Redis connection."""
    try:
        client = await get_redis_client()
        await client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        # Don't fail startup if Redis is not available
        pass


async def close_redis():
    """Close Redis connections."""
    global redis_client, redis_pool
    
    if redis_client:
        await redis_client.close()
        redis_client = None
    
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None


async def cache_get(key: str) -> Optional[Any]:
    """
    Get value from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None
    """
    try:
        client = await get_redis_client()
        value = await client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Cache get error for key {key}: {str(e)}")
        return None


async def cache_set(
    key: str,
    value: Any,
    ttl: Optional[int] = None
) -> bool:
    """
    Set value in cache.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds
        
    Returns:
        Success status
    """
    try:
        client = await get_redis_client()
        serialized = json.dumps(value)
        
        if ttl is None:
            ttl = settings.redis_cache_ttl
        
        await client.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.error(f"Cache set error for key {key}: {str(e)}")
        return False


async def cache_delete(key: str) -> bool:
    """
    Delete value from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Success status
    """
    try:
        client = await get_redis_client()
        await client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error for key {key}: {str(e)}")
        return False


async def cache_invalidate_pattern(pattern: str) -> int:
    """
    Invalidate cache keys matching pattern.
    
    Args:
        pattern: Key pattern (e.g., "knowledge:*")
        
    Returns:
        Number of keys deleted
    """
    try:
        client = await get_redis_client()
        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            deleted = await client.delete(*keys)
            logger.info(f"Invalidated {deleted} cache keys matching pattern: {pattern}")
            return deleted
        return 0
    except Exception as e:
        logger.error(f"Cache invalidation error for pattern {pattern}: {str(e)}")
        return 0