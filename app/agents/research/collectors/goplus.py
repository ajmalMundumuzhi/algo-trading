
import logging

import httpx


logger = logging.getLogger(__name__)


class GoPlusClient:
    BASE_URL = "https://api.gopluslabs.io/api/v1"

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers={
                "Accept": "application/json",
            },
        )

    async def check_token_security(
        self,
        chain_id: str,
        contract_address: str,
    ) -> dict:
        if not chain_id or not contract_address:
            raise ValueError(
                "Chain ID and contract address are required"
            )

        response = await self.client.get(
            f"/token_security/{chain_id}",
            params={
                "contract_addresses": contract_address.lower(),
            },
        )

        response.raise_for_status()

        payload = response.json()

        if payload.get("code") != 1:
            raise ValueError(
                f"GoPlus API error: {payload.get('message')}"
            )

        result = payload.get("result") or {}

        security_data = result.get(
            contract_address.lower()
        )

        if security_data is None:
            return {
                "security_data": None,
                "message": "No security data found for contract",
            }

        return {
            "security_data": security_data,
            "message": payload.get("message"),
        }

    async def close(self):
        await self.client.aclose()
