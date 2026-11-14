
import logging
import re

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

    @staticmethod
    def normalize(value: str) -> str:
        return re.sub(
            r"[^a-z0-9]",
            "",
            value.lower(),
        )

    def is_relevant_repository(
        self,
        project_name: str,
        repository: dict,
    ) -> bool:
        repo_name = repository.get("name", "")
        description = repository.get("description") or ""

        normalized_project = self.normalize(project_name)
        normalized_repo = self.normalize(repo_name)

        if not normalized_project or not normalized_repo:
            return False

        if normalized_project == normalized_repo:
            return True

        if (
            len(normalized_project) >= 5
            and normalized_project in normalized_repo
        ):
            return True

        normalized_description = self.normalize(description)

        return (
            len(normalized_project) >= 5
            and normalized_project in normalized_description
        )

    async def search_repositories(
        self,
        project_name: str,
    ) -> list[dict]:
        response = await self.client.get(
            "/search/repositories",
            params={
                "q": f'"{project_name}" in:name,description',
                "sort": "stars",
                "order": "desc",
                "per_page": 20,
            },
        )
        response.raise_for_status()

        data = response.json()

        return [
            repository
            for repository in data.get("items", [])
            if self.is_relevant_repository(
                project_name,
                repository,
            )
        ]

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
