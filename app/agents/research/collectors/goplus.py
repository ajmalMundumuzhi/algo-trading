
import httpx


class GoPlusClient:
    BASE_URL = "https://api.gopluslabs.io/api/v1"

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
        )

    async def check_token_security(
        self,
        chain_id: str,
        contract_address: str,
    ) -> dict:
        response = await self.client.get(
            "/token_security",
            params={
                "chain_id": chain_id,
                "contract_addresses": contract_address,
            },
        )
        response.raise_for_status()

        data = response.json()

        if data.get("code") != 1:
            raise ValueError(
                f"GoPlus API error: {data.get('message')}"
            )

        result = data.get("result", {})

        address = contract_address.lower()

        return {
            "chain_id": chain_id,
            "contract_address": address,
            "security_data": result.get(address),
            "source": "goplus",
        }

    async def close(self):
        await self.client.aclose()
