
import asyncio
import logging

from app.integrations.market_data.coingecko import CoinGeckoClient
from app.agents.research.data_collector import ResearchDataCollector
from app.agents.research.config import RESEARCH_CONFIG


logging.basicConfig(level=logging.INFO)


async def main():
    coingecko = CoinGeckoClient()
    collector = ResearchDataCollector()

    try:
        config = RESEARCH_CONFIG

        print("Fetching research candidates...")

        candidates = await coingecko.get_ranked_candidates(
            start_rank=config.min_market_cap_rank,
            end_rank=config.max_market_cap_rank,
        )

        print("Fetching DeFiLlama protocols...")

        protocols = await collector.defillama.get_protocols()

        print("Collecting project research data...")

        for candidate in candidates[:5]:
            result = await collector.collect_project_data(
                candidate=candidate,
                defillama_protocols=protocols,
            )

            print("\nPROJECT:", result["project"]["name"])
            print("SYMBOL:", result["project"]["symbol"])

            for source, details in result["sources"].items():
                print(f"\n{source.upper()}:")
                print("Status:", details["status"])

                if details.get("data"):
                    print("Data:", details["data"])
                else:
                    print("Reason:", details.get("reason"))

        print("\nRESEARCH DATA COLLECTION TEST COMPLETED")

    finally:
        await coingecko.close()
        await collector.close()


if __name__ == "__main__":
    asyncio.run(main())
