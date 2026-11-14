
import logging

import httpx


logger = logging.getLogger(__name__)


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if token:
            headers["Authorization"] = f"Bearer {token}"

        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=30.0,
        )

    async def search_repositories(
        self,
        project_name: str,
    ) -> list[dict]:
        response = await self.client.get(
            "/search/repositories",
            params={
                "q": f"{project_name} in:name",
                "sort": "updated",
                "order": "desc",
                "per_page": 10,
            },
        )
        response.raise_for_status()

        data = response.json()

        return data.get("items", [])

    async def get_repository_activity(
        self,
        owner: str,
        repository: str,
    ) -> dict:
        response = await self.client.get(
            f"/repos/{owner}/{repository}",
        )
        response.raise_for_status()

        repo = response.json()

        return {
            "name": repo.get("full_name"),
            "description": repo.get("description"),
            "stars": repo.get("stargazers_count"),
            "forks": repo.get("forks_count"),
            "open_issues": repo.get("open_issues_count"),
            "last_updated": repo.get("updated_at"),
            "default_branch": repo.get("default_branch"),
            "html_url": repo.get("html_url"),
        }

    async def close(self):
        await self.client.aclose()
