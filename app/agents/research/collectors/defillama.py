
import logging

import httpx


logger = logging.getLogger(__name__)


class DefiLlamaClient:
    BASE_URL = "https://api.llama.fi"

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            follow_redirects=True,
        )

    async def get_protocols(self) -> list[dict]:
        response = await self.client.get("/protocols")
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            raise ValueError("Invalid DefiLlama protocols response")

        return data

    async def get_protocol_details(
        self,
        protocol_slug: str,
    ) -> dict:
        response = await self.client.get(
            f"/protocol/{protocol_slug}"
        )
        response.raise_for_status()

        return response.json()

    async def find_protocol(
        self,
        coin_name: str,
    ) -> dict | None:
        protocols = await self.get_protocols()

        normalized_name = coin_name.strip().lower()

        matches = [
            protocol
            for protocol in protocols
            if protocol.get("name", "").strip().lower()
            == normalized_name
        ]

        if not matches:
            return None

        protocol = matches[0]

        return {
            "name": protocol.get("name"),
            "slug": protocol.get("slug"),
            "symbol": protocol.get("symbol"),
            "tvl": protocol.get("tvl"),
            "chains": protocol.get("chains", []),
            "category": protocol.get("category"),
            "source": "defillama",
        }

    async def close(self):
        await self.client.aclose()
