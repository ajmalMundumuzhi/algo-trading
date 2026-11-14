
import asyncio
import logging

from app.agents.research.config import RESEARCH_CONFIG
from app.integrations.market_data.coingecko import CoinGeckoClient


logging.basicConfig(level=logging.INFO)


async def main():
    client = CoinGeckoClient()

    try:
        config = RESEARCH_CONFIG

        candidates = await client.get_ranked_candidates(
            start_rank=config.min_market_cap_rank,
            end_rank=config.max_market_cap_rank,
        )

        print("\nSMALL-CAP RESEARCH CANDIDATES")
        print("============================")
        print("Total candidates:", len(candidates))

        for coin in candidates[:20]:
            print(
                coin.get("market_cap_rank"),
                coin.get("name"),
                coin.get("symbol"),
                coin.get("market_cap"),
            )

        print("\nCANDIDATE COLLECTION COMPLETED")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
