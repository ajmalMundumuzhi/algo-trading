import asyncio
import logging
import re

from urllib.parse import urlparse

from app.agents.research.collectors.defillama import (
    DefiLlamaClient,
)
from app.agents.research.collectors.github import GitHubClient
from app.agents.research.collectors.goplus import GoPlusClient
from app.integrations.market_data.coingecko import CoinGeckoClient


logger = logging.getLogger(__name__)


class ResearchDataCollector:
    DEFILLAMA_ALIASES = {
        "origintrail": ["OriginTrail"],
        "thetanetwork": ["Theta Network"],
        "crvusd": ["Curve USD"],
    }

    EVM_ADDRESS_PATTERN = re.compile(
        r"^0x[a-fA-F0-9]{40}$"
    )

    def __init__(self, github_token: str | None = None):
        self.defillama = DefiLlamaClient()
        self.github = GitHubClient(token=github_token)
        self.goplus = GoPlusClient()

        try:
            self.coingecko = CoinGeckoClient()
        except Exception as error:
            logger.warning(
                "CoinGecko research unavailable: %s",
                error,
            )
            self.coingecko = None

    @staticmethod
    def _normalize(value: str | None) -> str:
        return "".join(
            character.lower()
            for character in (value or "").strip()
            if character.isalnum()
        )

    @staticmethod
    def _extract_github_repository(url: str) -> str | None:
        if not isinstance(url, str):
            return None

        try:
            parsed = urlparse(url.strip())

            if parsed.hostname not in {
                "github.com",
                "www.github.com",
            }:
                return None

            parts = [
                part
                for part in parsed.path.strip("/").split("/")
                if part
            ]

            if len(parts) < 2:
                return None

            owner = parts[0]
            repository = parts[1].removesuffix(".git")

            if not owner or not repository:
                return None

            if owner.lower() in {
                "features",
                "topics",
                "collections",
                "marketplace",
                "settings",
                "login",
                "signup",
            }:
                return None

            return f"{owner}/{repository}"

        except (TypeError, ValueError):
            return None

    async def _get_official_github_repositories(
        self,
        coin_id: str | None,
    ) -> dict:
        if not self.coingecko:
            return {
                "repositories": [],
                "status": "unavailable",
                "reason": "CoinGecko client is not configured",
            }

        if not coin_id:
            return {
                "repositories": [],
                "status": "unavailable",
                "reason": "CoinGecko ID is missing",
            }

        try:
            details = await self.coingecko.get_coin_details(
                coin_id
            )

            links = details.get("links") or {}
            repository_links = (
                (links.get("repos_url") or {})
                .get("github") or []
            )

            repositories = []

            for url in repository_links:
                repository = self._extract_github_repository(
                    url
                )

                if repository and repository.lower() not in {
                    item.lower()
                    for item in repositories
                }:
                    repositories.append(repository)

            return {
                "repositories": repositories,
                "status": "available",
                "reason": (
                    "GitHub links retrieved from CoinGecko project profile"
                ),
            }

        except Exception as error:
            logger.warning(
                "Could not retrieve official GitHub links for %s: %s",
                coin_id,
                error,
            )

            return {
                "repositories": [],
                "status": "error",
                "reason": str(error),
            }

    @classmethod
    def _find_defillama_protocol(
        cls,
        coin_name: str,
        protocols: list[dict],
    ) -> dict | None:
        normalized_names = {
            cls._normalize(coin_name)
        }

        aliases = cls.DEFILLAMA_ALIASES.get(
            cls._normalize(coin_name),
            [],
        )

        normalized_names.update(
            cls._normalize(alias)
            for alias in aliases
        )

        matches = [
            protocol
            for protocol in protocols
            if cls._normalize(
                protocol.get("name")
            ) in normalized_names
        ]

        if not matches:
            return None

        if len(matches) > 1:
            logger.warning(
                "Multiple DeFiLlama matches found for %s",
                coin_name,
            )

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

    async def _collect_github(
        self,
        project_name: str,
        coin_id: str | None,
    ) -> dict:
        official_result = (
            await self._get_official_github_repositories(
                coin_id
            )
        )

        official_repositories = (
            official_result["repositories"]
        )

        if not official_repositories:
            return {
                "status": "unverified",
                "data": None,
                "reason": (
                    official_result.get("reason")
                    or (
                        "No GitHub repository is listed in "
                        "the CoinGecko project profile."
                    )
                ),
                "matched_repository": None,
                "verification_source": None,
                "official_repositories": [],
                "failed_repositories": [],
                "candidates": [],
            }

        failed_repositories = []

        for repository in official_repositories:
            if "/" not in repository:
                failed_repositories.append({
                    "repository": repository,
                    "reason": "Invalid repository format",
                })
                continue

            owner, repository_name = repository.split(
                "/",
                1,
            )

            try:
                details = (
                    await self.github.get_repository_activity(
                        owner,
                        repository_name,
                        verified=True,
                        verification_status=(
                            "listed_in_coingecko_project_profile"
                        ),
                    )
                )

                canonical_name = details.get("repository")

                if (
                    not canonical_name
                    or canonical_name.lower()
                    != repository.lower()
                ):
                    failed_repositories.append({
                        "repository": repository,
                        "reason": (
                            "GitHub repository identity did not "
                            "match the CoinGecko profile link"
                        ),
                    })
                    continue

                return {
                    "status": "available",
                    "data": details,
                    "reason": (
                        "Repository exists on GitHub and matches "
                        "a repository link listed in the CoinGecko "
                        "project profile."
                    ),
                    "matched_repository": canonical_name,
                    "verification_source": (
                        "coingecko_project_profile"
                    ),
                    "official_repositories": official_repositories,
                    "failed_repositories": failed_repositories,
                    "candidates": [],
                }

            except Exception as error:
                logger.warning(
                    "Official GitHub repository check failed for %s: %s",
                    repository,
                    error,
                )

                failed_repositories.append({
                    "repository": repository,
                    "reason": str(error),
                })

        return {
            "status": "error",
            "data": None,
            "reason": (
                "GitHub repositories listed in the CoinGecko "
                "profile could not be verified."
            ),
            "matched_repository": None,
            "verification_source": None,
            "official_repositories": official_repositories,
            "failed_repositories": failed_repositories,
            "candidates": [],
        }

    async def _collect_defillama(
        self,
        project_name: str,
        protocols: list[dict],
    ) -> dict:
        try:
            protocol = self._find_defillama_protocol(
                project_name,
                protocols,
            )

            if protocol is None:
                return {
                    "status": "unavailable",
                    "data": None,
                    "reason": (
                        "No exact or configured alias match found"
                    ),
                }

            slug = protocol.get("slug")

            if not slug:
                return {
                    "status": "partial",
                    "data": protocol,
                    "reason": "Protocol slug unavailable",
                }

            details = await self.defillama.get_protocol_details(
                slug
            )

            return {
                "status": "available",
                "data": {
                    **protocol,
                    "details": details,
                },
            }

        except Exception as error:
            logger.exception(
                "DeFiLlama research failed for %s",
                project_name,
            )

            return {
                "status": "error",
                "data": None,
                "reason": str(error),
            }

    async def _collect_token_contract(
        self,
        coin_id: str | None,
    ) -> dict:
        if not self.coingecko:
            return {
                "status": "unavailable",
                "data": None,
                "reason": "CoinGecko client is not configured",
            }

        if not coin_id:
            return {
                "status": "unavailable",
                "data": None,
                "reason": "CoinGecko ID is missing",
            }

        try:
            contract = (
                await self.coingecko.get_verified_token_contract(
                    coin_id
                )
            )

            if not contract:
                return {
                    "status": "unavailable",
                    "data": None,
                    "reason": (
                        "No supported EVM contract address found"
                    ),
                }

            address = contract.get("contract_address")
            chain_id = contract.get("chain_id")

            if (
                not address
                or not chain_id
                or not self.EVM_ADDRESS_PATTERN.fullmatch(address)
            ):
                return {
                    "status": "unavailable",
                    "data": None,
                    "reason": "Contract mapping failed validation",
                }

            return {
                "status": "available",
                "data": contract,
                "reason": (
                    "Contract address discovered through CoinGecko. "
                    "This does not independently verify contract safety."
                ),
            }

        except Exception as error:
            logger.exception(
                "CoinGecko contract discovery failed for %s",
                coin_id,
            )

            return {
                "status": "error",
                "data": None,
                "reason": str(error),
            }

    async def _collect_goplus(
        self,
        token_contract: dict | None,
    ) -> dict:
        if not token_contract:
            return {
                "status": "unavailable",
                "data": None,
                "reason": "No supported token contract mapping found",
            }

        chain_id = token_contract.get("chain_id")
        contract_address = token_contract.get("contract_address")
        platform = token_contract.get("platform")

        if not chain_id or not contract_address:
            return {
                "status": "unavailable",
                "data": None,
                "reason": "Token contract mapping is incomplete",
            }

        if not self.EVM_ADDRESS_PATTERN.fullmatch(
            contract_address
        ):
            return {
                "status": "unavailable",
                "data": None,
                "reason": "Contract address format is invalid",
            }

        try:
            result = await self.goplus.check_token_security(
                chain_id=str(chain_id),
                contract_address=contract_address,
            )

            if not result or result.get("security_data") is None:
                return {
                    "status": "unavailable",
                    "data": None,
                    "reason": "No security data returned for this contract",
                }

            return {
                "status": "available",
                "data": {
                    **result,
                    "contract_mapping": {
                        "chain_id": str(chain_id),
                        "contract_address": contract_address,
                        "platform": platform,
                        "mapping_source": token_contract.get("source"),
                    },
                },
            }

        except Exception as error:
            logger.exception(
                "GoPlus security lookup failed for %s",
                contract_address,
            )

            return {
                "status": "error",
                "data": None,
                "reason": str(error),
            }

    async def collect_project_data(
        self,
        candidate: dict,
        defillama_protocols: list[dict],
        token_contract: dict | None = None,
    ) -> dict:
        project_name = candidate.get("name")
        coin_id = candidate.get("id")

        if not project_name:
            raise ValueError(
                "Candidate must contain a project name"
            )

        github_task = self._collect_github(
            project_name,
            coin_id,
        )

        defillama_task = self._collect_defillama(
            project_name,
            defillama_protocols,
        )

        if token_contract:
            contract_task = asyncio.sleep(
                0,
                result={
                    "status": "available",
                    "data": token_contract,
                    "reason": "Contract mapping supplied by caller",
                },
            )
        else:
            contract_task = self._collect_token_contract(
                coin_id
            )

        (
            github_result,
            defillama_result,
            contract_result,
        ) = await asyncio.gather(
            github_task,
            defillama_task,
            contract_task,
        )

        contract_data = (
            contract_result.get("data")
            if contract_result.get("status") == "available"
            else None
        )

        goplus_result = await self._collect_goplus(
            contract_data
        )

        return {
            "project": {
                "name": project_name,
                "symbol": candidate.get("symbol"),
                "coingecko_id": coin_id,
                "market_cap": candidate.get("market_cap"),
                "market_cap_rank": candidate.get("market_cap_rank"),
                "current_price": candidate.get("current_price"),
                "total_volume": candidate.get("total_volume"),
            },
            "sources": {
                "defillama": defillama_result,
                "github": github_result,
                "token_contract": contract_result,
                "goplus": goplus_result,
            },
        }

    async def close(self):
        clients = [
            self.defillama.close(),
            self.github.close(),
            self.goplus.close(),
        ]

        if self.coingecko:
            clients.append(self.coingecko.close())

        await asyncio.gather(
            *clients,
            return_exceptions=True,
        )
