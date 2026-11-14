
import asyncio
import logging

from app.agents.research.collectors.defillama import (
    DefiLlamaClient,
)


logging.basicConfig(level=logging.INFO)


async def main():
    client = DefiLlamaClient()

    try:
        protocols = await client.get_protocols()

        print("\nDEFILLAMA DATA TEST")
        print("===================")
        print("Protocols retrieved:", len(protocols))

        for protocol in protocols[:10]:
            print(
                protocol.get("name"),
                protocol.get("tvl"),
                protocol.get("chains"),
            )

        print("\nDEFI LLAMA TEST COMPLETED")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
