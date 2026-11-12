import asyncio
import logging

logger = logging.getLogger(__name__)


async def retry_async(
    operation,
    *,
    retries: int = 3,
    base_delay: float = 1.0,
    retry_on: tuple = (Exception,),
):
    for attempt in range(retries + 1):
        try:
            return await operation()

        except retry_on:
            if attempt == retries:
                logger.exception(
                    "Operation failed after %s attempts",
                    retries + 1,
                )
                raise

            delay = base_delay * (2 ** attempt)

            logger.warning(
                "Operation failed. Retrying in %.1f seconds. Attempt %s/%s",
                delay,
                attempt + 1,
                retries,
            )

            await asyncio.sleep(delay)