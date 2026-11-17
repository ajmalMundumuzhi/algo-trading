import asyncio
import logging
import re

from datetime import datetime, timedelta, timezone

import httpx


logger = logging.getLogger(__name__)


class GitHubClient:
    BASE_URL = "https://api.github.com"
    COMMIT_LOOKBACK_DAYS = 90

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

    async def _get_optional(
        self,
        endpoint: str,
        params: dict | None = None,
    ):
        try:
            response = await self.client.get(
                endpoint,
                params=params,
            )

            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as error:
            logger.warning(
                "GitHub endpoint failed: %s HTTP %s",
                endpoint,
                error.response.status_code,
            )

        except httpx.HTTPError:
            logger.exception(
                "GitHub request failed: %s",
                endpoint,
            )

        return None

    @staticmethod
    def _parse_commit_date(
        commit: dict,
    ) -> datetime | None:
        commit_data = commit.get("commit") or {}
        author_data = commit_data.get("author") or {}

        date_value = author_data.get("date")

        if not date_value:
            return None

        try:
            return datetime.fromisoformat(
                date_value.replace("Z", "+00:00")
            )

        except (TypeError, ValueError):
            return None

    async def _get_recent_commits(
        self,
        owner: str,
        repository: str,
    ) -> list[dict] | None:
        commits = await self._get_optional(
            f"/repos/{owner}/{repository}/commits",
            params={
                "per_page": 100,
            },
        )

        if not isinstance(commits, list):
            return None

        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(days=self.COMMIT_LOOKBACK_DAYS)
        )

        recent_commits = []

        for item in commits:
            if not isinstance(item, dict):
                continue

            commit_date = self._parse_commit_date(item)

            if commit_date is None:
                continue

            if commit_date.tzinfo is None:
                commit_date = commit_date.replace(
                    tzinfo=timezone.utc
                )

            if commit_date < cutoff:
                continue

            recent_commits.append({
                "sha": item.get("sha"),
                "message": (
                    (item.get("commit") or {})
                    .get("message")
                ),
                "date": commit_date.isoformat(),
                "url": item.get("html_url"),
                "author": (
                    (item.get("author") or {})
                    .get("login")
                ),
            })

        return recent_commits

    async def _get_contributors_count(
        self,
        owner: str,
        repository: str,
    ) -> int | None:
        contributors = await self._get_optional(
            f"/repos/{owner}/{repository}/contributors",
            params={
                "per_page": 100,
            },
        )

        if not isinstance(contributors, list):
            return None

        return len(contributors)

    async def get_repository_activity(
        self,
        owner: str,
        repository: str,
        verified: bool = False,
        verification_status: str = "pending_manual_verification",
    ) -> dict:
        repo = await self._get_optional(
            f"/repos/{owner}/{repository}"
        )

        if not isinstance(repo, dict):
            raise ValueError(
                "Could not retrieve GitHub repository details"
            )

        canonical_name = repo.get("full_name")

        if (
            not canonical_name
            or canonical_name.lower()
            != f"{owner}/{repository}".lower()
        ):
            raise ValueError(
                "GitHub returned a different repository identity"
            )

        commits_task = self._get_recent_commits(
            owner,
            repository,
        )

        contributors_task = self._get_contributors_count(
            owner,
            repository,
        )

        recent_commits, contributors_count = (
            await asyncio.gather(
                commits_task,
                contributors_task,
            )
        )

        return {
            "repository": canonical_name,
            "name": repo.get("name"),
            "description": repo.get("description"),
            "stars": repo.get("stargazers_count"),
            "forks": repo.get("forks_count"),
            "open_issues": repo.get("open_issues_count"),
            "last_updated": repo.get("updated_at"),
            "created_at": repo.get("created_at"),
            "default_branch": repo.get("default_branch"),
            "html_url": repo.get("html_url"),
            "recent_commits": recent_commits or [],
            "recent_commit_count": (
                len(recent_commits)
                if recent_commits is not None
                else None
            ),
            "recent_commits_available": (
                recent_commits is not None
            ),
            "contributors_count": contributors_count,
            "commit_lookback_days": self.COMMIT_LOOKBACK_DAYS,
            "verified": verified,
            "verification_status": verification_status,
        }

    async def close(self):
        await self.client.aclose()