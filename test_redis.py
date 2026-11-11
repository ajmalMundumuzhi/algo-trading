
import asyncio

from app.core.redis import (
    check_redis_connection,
    close_redis_connection,
)


async def main():
    try:
        connected = await check_redis_connection()

        if connected:
            print("Redis connection successful!")
            print("Redis server is responding.")
        else:
            print("Redis connection failed!")

    finally:
        await close_redis_connection()


asyncio.run(main())
