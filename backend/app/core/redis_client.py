import redis.asyncio as redis
from app.core.config import settings
from loguru import logger
from typing import Optional
import json


redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """FastAPI dependency — returns the shared Redis client."""
    return redis_client


async def init_redis():
    global redis_client
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    await redis_client.ping()
    logger.info("Redis connected successfully")


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


# ── Cache Helpers ────────────────────────────────────────────────
async def cache_set(key: str, value: dict, ttl: int = settings.CACHE_TTL_SECONDS):
    """Serialize dict and store in Redis with TTL."""
    if redis_client:
        await redis_client.setex(key, ttl, json.dumps(value))


async def cache_get(key: str) -> Optional[dict]:
    """Retrieve and deserialize a cached value."""
    if redis_client:
        raw = await redis_client.get(key)
        if raw:
            return json.loads(raw)
    return None


async def cache_delete(key: str):
    if redis_client:
        await redis_client.delete(key)
