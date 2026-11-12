import asyncio
import ccxt

from app.utils.retry import retry_async

attempts = 0


async def unstable_request():
    global attempts
    attempts += 1

    if attempts == 1:
        raise ccxt.NetworkError("Simulated network failure")

    return {"status": "success"}


async def main():
    global attempts

    result = await retry_async(
        unstable_request,
        retries=3,
        base_delay=0.1,
        retry_on=(ccxt.NetworkError,),
    )

    print("Total attempts:", attempts)
    print("API result:", result)


if __name__ == "__main__":
    asyncio.run(main())