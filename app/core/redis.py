
import redis.asyncio as redis

from app.core.config import settings

redis_client = redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def check_redis_connection() -> bool:
    try:
        return await redis_client.ping()
    except redis.RedisError:
        return False


async def close_redis_connection() -> None:
    await redis_client.aclose()
