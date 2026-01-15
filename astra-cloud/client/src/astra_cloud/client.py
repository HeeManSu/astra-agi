"""
Astra Cloud client for accessing cloud resources.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel

from astra_cloud.exceptions import (
    AstraCloudError,
    AuthenticationError,
    ConnectionError,
    NotFoundError,
)


if TYPE_CHECKING:
    pass


class AstraCloudConfig(BaseModel):
    """Configuration for Astra Cloud client."""

    api_url: str
    api_key: str
    project_id: str
    timeout: float = 30.0


class AstraCloud:
    """
    Astra Cloud Python SDK client.

    Provides access to agents, teams, and workflows stored in Astra Cloud.

    Example:
        ```python
        from astra_cloud import AstraCloud

        cloud = AstraCloud(
            api_url="https://api.astra.cloud", api_key="your-api-key", project_id="your-project-id"
        )

        # Fetch agents from cloud
        agents = await cloud.get_agents()

        # Fetch teams from cloud
        teams = await cloud.get_teams()

        # Fetch a specific agent
        agent = await cloud.get_agent("agent-id")
        ```
    """

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        project_id: str | None = None,
        timeout: float = 30.0,
    ):
        """
        Initialize Astra Cloud client.

        Args:
            api_url: Astra Cloud API URL. Defaults to ASTRA_CLOUD_API env var.
            api_key: API key for authentication. Defaults to ASTRA_API_KEY env var.
            project_id: Project ID. Defaults to ASTRA_PROJECT_ID env var.
            timeout: Request timeout in seconds.

        Raises:
            AstraCloudError: If required configuration is missing.
        """
        self.config = AstraCloudConfig(
            api_url=api_url or os.getenv("ASTRA_CLOUD_API", ""),
            api_key=api_key or os.getenv("ASTRA_API_KEY", ""),
            project_id=project_id or os.getenv("ASTRA_PROJECT_ID", ""),
            timeout=timeout,
        )

        self._validate_config()

        self._client = httpx.AsyncClient(
            base_url=self.config.api_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=self.config.timeout,
        )

    def _validate_config(self) -> None:
        """Validate that all required configuration is present."""
        if not self.config.api_url:
            raise AstraCloudError(
                "ASTRA_CLOUD_API is required. "
                "Set it via parameter or ASTRA_CLOUD_API environment variable."
            )
        if not self.config.api_key:
            raise AstraCloudError(
                "ASTRA_API_KEY is required. "
                "Set it via parameter or ASTRA_API_KEY environment variable."
            )
        if not self.config.project_id:
            raise AstraCloudError(
                "ASTRA_PROJECT_ID is required. "
                "Set it via parameter or ASTRA_PROJECT_ID environment variable."
            )

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated request to the API."""
        url = f"/projects/{self.config.project_id}{endpoint}"

        try:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key") from e
            if e.response.status_code == 404:
                raise NotFoundError(f"Resource not found: {endpoint}") from e
            raise AstraCloudError(f"API error: {e.response.status_code} - {e.response.text}") from e
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to Astra Cloud: {self.config.api_url}") from e

    async def get_agents(self) -> list[dict[str, Any]]:
        """
        Fetch all agents from the cloud project.

        Returns:
            List of agent definitions.

        Raises:
            AstraCloudError: If the request fails.
        """
        response = await self._request("GET", "/agents")
        return response.get("data", {}).get("agents", [])

    async def get_agent(self, agent_id: str) -> dict[str, Any]:
        """
        Fetch a specific agent by ID.

        Args:
            agent_id: The agent ID.

        Returns:
            Agent definition.

        Raises:
            NotFoundError: If agent not found.
            AstraCloudError: If the request fails.
        """
        response = await self._request("GET", f"/agents/{agent_id}")
        return response.get("data", {}).get("agent", {})

    async def get_teams(self) -> list[dict[str, Any]]:
        """
        Fetch all teams from the cloud project.

        Returns:
            List of team definitions.

        Raises:
            AstraCloudError: If the request fails.
        """
        response = await self._request("GET", "/teams")
        return response.get("data", {}).get("teams", [])

    async def get_team(self, team_id: str) -> dict[str, Any]:
        """
        Fetch a specific team by ID.

        Args:
            team_id: The team ID.

        Returns:
            Team definition.

        Raises:
            NotFoundError: If team not found.
            AstraCloudError: If the request fails.
        """
        response = await self._request("GET", f"/teams/{team_id}")
        return response.get("data", {}).get("team", {})

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> AstraCloud:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
