"""
Astra Cloud Python SDK

Access agents, teams, and workflows from Astra Cloud.

Example usage:
    from astra_cloud import AstraCloud

    cloud = AstraCloud(
        api_url="https://api.astra.cloud",
        api_key="your-api-key",
        project_id="your-project-id"
    )

    # Get all agents
    agents = await cloud.get_agents()

    # Get all teams
    teams = await cloud.get_teams()
"""

from astra_cloud.agents import get_agents_from_cloud
from astra_cloud.client import AstraCloud
from astra_cloud.exceptions import (
    AstraCloudError,
    AuthenticationError,
    ConnectionError,
    NotFoundError,
)
from astra_cloud.teams import get_teams_from_cloud


__version__ = "0.1.0"

__all__ = [
    "AstraCloud",
    "AstraCloudError",
    "AuthenticationError",
    "ConnectionError",
    "NotFoundError",
    "get_agents_from_cloud",
    "get_teams_from_cloud",
]
