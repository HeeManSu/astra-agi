"""
Team-related cloud operations.
"""

from __future__ import annotations

from typing import Any

from astra_cloud.client import AstraCloud


async def get_teams_from_cloud(
    api_url: str | None = None,
    api_key: str | None = None,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Convenience function to fetch all teams from Astra Cloud.

    This is a shorthand for creating an AstraCloud client and calling get_teams().

    Args:
        api_url: Astra Cloud API URL. Defaults to ASTRA_CLOUD_API env var.
        api_key: API key for authentication. Defaults to ASTRA_API_KEY env var.
        project_id: Project ID. Defaults to ASTRA_PROJECT_ID env var.

    Returns:
        List of team definitions.

    Example:
        ```python
        from astra_cloud import get_teams_from_cloud

        teams = await get_teams_from_cloud(
            api_url="https://api.astra.cloud", api_key="your-api-key", project_id="your-project-id"
        )

        for team in teams:
            print(team["name"])
        ```
    """
    async with AstraCloud(
        api_url=api_url,
        api_key=api_key,
        project_id=project_id,
    ) as cloud:
        return await cloud.get_teams()
