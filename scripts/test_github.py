
import asyncio
import json

from app.core.config import settings
from app.agents.research.collectors.github import GitHubClient


async def main():
    github_token = (
        settings.github_token.get_secret_value()
        if settings.github_token
        else None
    )

    client = GitHubClient(token=github_token)

    try:
        print(
            "GitHub authentication configured:",
            bool(github_token),
        )

        repositories = await client.search_repositories(
            "OriginTrail"
        )

        print("\nRepository candidates:")
        print(json.dumps(repositories[:5], indent=4))

        if repositories:
            repository = repositories[0]
            full_name = repository.get("full_name")

            if full_name and "/" in full_name:
                owner, name = full_name.split("/", 1)

                activity = await client.get_repository_activity(
                    owner,
                    name,
                )

                print("\nRepository activity:")
                print(json.dumps(activity, indent=4))

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
