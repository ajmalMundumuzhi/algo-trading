
import asyncio
import logging

from app.agents.research.collectors.defillama import (
    DefiLlamaClient,
)
from app.agents.research.collectors.github import GitHubClient
from app.agents.research.collectors.goplus import GoPlusClient


logger = logging.getLogger(__name__)


class ResearchDataCollector:
    def __init__(self, github_token: str | None = None):
        self.defillama = DefiLlamaClient()
        self.github = GitHubClient(token=github_token)
        self.goplus = GoPlusClient()

    @staticmethod
    def _find_defillama_protocol(
        coin_name: str,
        protocols: list[dict],
    ) -> dict | None:
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

    async def _collect_github(
        self,
        project_name: str,
    ) -> dict:
        try:
            repositories = await self.github.search_repositories(
                project_name
            )

            if not repositories:
                return {
                    "status": "unavailable",
                    "data": None,
                    "reason": "No relevant repository name or description match",
                }

            return {
                "status": "unverified",
                "data": None,
                "reason": "Repository match requires official project verification",
                "candidates": [
                    {
                        "name": repo.get("full_name"),
                        "url": repo.get("html_url"),
                        "description": repo.get("description"),
                        "stars": repo.get("stargazers_count"),
                    }
                    for repo in repositories[:5]
                ],
            }

            repository = repositories[0]
            full_name = repository.get("full_name")

            if not full_name or "/" not in full_name:
                return {
                    "status": "unavailable",
                    "data": None,
                    "reason": "Repository identity is incomplete",
                }

            owner, name = full_name.split("/", 1)

            details = await self.github.get_repository_activity(
                owner,
                name,
            )

            return {
                "status": "available",
                "data": details,
                "matched_repository": full_name,
            }

        except Exception as error:
            logger.exception(
                "GitHub research failed for %s",
                project_name,
            )

            return {
                "status": "error",
                "data": None,
                "reason": str(error),
            }

    @staticmethod
    def _collect_defillama(
        project_name: str,
        protocols: list[dict],
    ) -> dict:
        try:
            protocol = ResearchDataCollector._find_defillama_protocol(
                project_name,
                protocols,
            )

            if protocol is None:
                return {
                    "status": "unavailable",
                    "data": None,
                    "reason": "No exact protocol-name match",
                }

            return {
                "status": "available",
                "data": protocol,
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

    async def _collect_goplus(
        self,
        token_contract: dict | None,
    ) -> dict:
        if not token_contract:
            return {
                "status": "unavailable",
                "data": None,
                "reason": "No verified token contract mapping supplied",
            }

        chain_id = token_contract.get("chain_id")
        contract_address = token_contract.get("contract_address")

        if not chain_id or not contract_address:
            return {
                "status": "unavailable",
                "data": None,
                "reason": "Token contract mapping is incomplete",
            }

        try:
            result = await self.goplus.check_token_security(
                chain_id=str(chain_id),
                contract_address=contract_address,
            )

            if result.get("security_data") is None:
                return {
                    "status": "unavailable",
                    "data": None,
                    "reason": "No security data returned for this contract",
                }

            return {
                "status": "available",
                "data": result,
            }

        except Exception as error:
            logger.exception("GoPlus security lookup failed")

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

        if not project_name:
            raise ValueError("Candidate must contain a project name")

        github_task = self._collect_github(project_name)
        goplus_task = self._collect_goplus(token_contract)

        github_result, goplus_result = await asyncio.gather(
            github_task,
            goplus_task,
        )

        defillama_result = self._collect_defillama(
            project_name,
            defillama_protocols,
        )

        return {
            "project": {
                "name": project_name,
                "symbol": candidate.get("symbol"),
                "coingecko_id": candidate.get("id"),
                "market_cap": candidate.get("market_cap"),
                "market_cap_rank": candidate.get("market_cap_rank"),
                "current_price": candidate.get("current_price"),
                "total_volume": candidate.get("total_volume"),
            },
            "sources": {
                "defillama": defillama_result,
                "github": github_result,
                "goplus": goplus_result,
            },
        }

    async def close(self):
        await asyncio.gather(
            self.defillama.close(),
            self.github.close(),
            self.goplus.close(),
            return_exceptions=True,
        )
