
import asyncio
import logging
import math
import re

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class CoinGeckoClient:
    BASE_URL = "https://api.coingecko.com/api/v3"
    MAX_ATTEMPTS = 3
    PAGE_SIZE = 250

    SUPPORTED_GOPLUS_CHAINS = {
        "ethereum": "1",
        "binance-smart-chain": "56",
        "polygon-pos": "137",
        "arbitrum-one": "42161",
        "optimistic-ethereum": "10",
        "avalanche": "43114",
        "base": "8453",
    }

    EVM_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")

    def __init__(self):
        api_key = settings.coingecko_api_key

        if not api_key:
            raise ValueError(
                "CoinGecko API key is not configured."
            )

        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "x-cg-demo-api-key": api_key.get_secret_value()
            },
            timeout=30.0,
        )

    async def _get_with_retry(
        self,
        endpoint: str,
        params: dict,
    ):
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                response = await self.client.get(
                    endpoint,
                    params=params,
                )

                should_retry = (
                    response.status_code == 429
                    or 500 <= response.status_code <= 599
                )

                if not should_retry:
                    response.raise_for_status()
                    return response.json()

                if attempt == self.MAX_ATTEMPTS:
                    response.raise_for_status()

                retry_after = response.headers.get("Retry-After")

                try:
                    delay = (
                        float(retry_after)
                        if retry_after
                        else 2 ** (attempt - 1)
                    )
                except ValueError:
                    delay = 2 ** (attempt - 1)

                delay = min(max(delay, 1), 30)

                logger.warning(
                    "CoinGecko HTTP %s. Retrying in %s seconds. "
                    "Attempt %s/%s",
                    response.status_code,
                    delay,
                    attempt,
                    self.MAX_ATTEMPTS,
                )

                await asyncio.sleep(delay)

            except httpx.TransportError as error:
                if attempt == self.MAX_ATTEMPTS:
                    logger.error(
                        "CoinGecko request failed after %s attempts: %s",
                        self.MAX_ATTEMPTS,
                        error,
                    )
                    raise

                delay = 2 ** (attempt - 1)

                logger.warning(
                    "CoinGecko network error. Retrying in %s seconds. "
                    "Attempt %s/%s",
                    delay,
                    attempt,
                    self.MAX_ATTEMPTS,
                )

                await asyncio.sleep(delay)

    
    async def get_top_coins(self, limit: int = 200) -> list[dict]:
        if limit < 1:
            raise ValueError("Coin limit must be positive")

        coins = []
        total_pages = math.ceil(limit / self.PAGE_SIZE)

        for page in range(1, total_pages + 1):
            remaining = limit - len(coins)
            per_page = min(remaining, self.PAGE_SIZE)

            page_coins = await self._get_with_retry(
                "/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": per_page,
                    "page": page,
                    "sparkline": "false",
                },
            )

            coins.extend(page_coins)

            if len(page_coins) < per_page:
                break

        logger.info(
            "Retrieved %s coins from CoinGecko (requested %s)",
            len(coins),
            limit,
        )

        return coins


    async def get_ranked_candidates(
        self,
        start_rank: int = 101,
        end_rank: int = 500,
    ) -> list[dict]:
        if start_rank < 1 or end_rank < start_rank:
            raise ValueError("Invalid market-cap rank range")

        first_page = ((start_rank - 1) // self.PAGE_SIZE) + 1
        last_page = math.ceil(end_rank / self.PAGE_SIZE)

        candidates = []

        for page in range(first_page, last_page + 1):
            coins = await self._get_with_retry(
                "/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": self.PAGE_SIZE,
                    "page": page,
                    "sparkline": "false",
                },
            )

            for coin in coins:
                rank = coin.get("market_cap_rank")

                if (
                    rank is not None
                    and start_rank <= rank <= end_rank
                ):
                    candidates.append(coin)

        candidates.sort(
            key=lambda coin: coin["market_cap_rank"]
        )

        logger.info(
            "Retrieved %s research candidates from ranks %s-%s",
            len(candidates),
            start_rank,
            end_rank,
        )

        return candidates

    async def get_coin_details(
        self,
        coin_id: str,
    ) -> dict:
        if not coin_id:
            raise ValueError("CoinGecko coin ID is required")

        return await self._get_with_retry(
            f"/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "false",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false",
            },
        )

    async def get_verified_token_contract(
        self,
        coin_id: str,
    ) -> dict | None:
        details = await self.get_coin_details(coin_id)

        platforms = details.get("platforms") or {}

        for platform, chain_id in self.SUPPORTED_GOPLUS_CHAINS.items():
            contract_address = platforms.get(platform)

            if not contract_address:
                continue

            if not self.EVM_ADDRESS_PATTERN.fullmatch(
                contract_address
            ):
                logger.warning(
                    "Invalid EVM contract address for %s on %s",
                    coin_id,
                    platform,
                )
                continue

            return {
                "chain_id": chain_id,
                "contract_address": contract_address,
                "platform": platform,
                "coingecko_id": coin_id,
                "source": "coingecko",
            }

        return None

    async def get_coin_list(self):
        return await self._get_with_retry(
            "/coins/list",
            params={"include_platform": "true"},
        )

    async def close(self):
        await self.client.aclose()
