"""
Team API Client.

Client for testing team APIs from backend using httpx.
Allows testing APIs programmatically without external HTTP calls.
"""

from collections.abc import AsyncIterator
import json
from typing import Any

import httpx


class TeamAPIClient:
    """
    Client for testing team APIs from backend.

    Allows testing APIs programmatically without external HTTP calls.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize API client.

        Args:
            base_url: Base URL of the server (default: http://localhost:8000)
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def list_teams(self) -> list[dict[str, Any]]:
        """
        List all teams via API.

        Returns:
            List of team metadata dictionaries
        """
        response = await self.client.get("/api/v1/teams")
        response.raise_for_status()
        return response.json()

    async def get_team(self, team_id: str) -> dict[str, Any]:
        """
        Get team details via API.

        Args:
            team_id: Team identifier

        Returns:
            Team details dictionary
        """
        response = await self.client.get(f"/api/v1/teams/{team_id}")
        response.raise_for_status()
        return response.json()

    async def generate(
        self,
        team_id: str,
        message: str,
        thread_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Invoke team via API (non-streaming).

        Args:
            team_id: Team identifier
            message: User message
            thread_id: Optional thread ID for conversation continuity
            temperature: Optional model temperature
            max_tokens: Optional max tokens

        Returns:
            Response dictionary with content and thread_id
        """
        payload: dict[str, Any] = {"message": message}
        if thread_id:
            payload["thread_id"] = thread_id
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        response = await self.client.post(
            f"/api/v1/teams/{team_id}/generate",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def stream(
        self,
        team_id: str,
        message: str,
        thread_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream team execution via API (SSE).

        Args:
            team_id: Team identifier
            message: User message
            thread_id: Optional thread ID for conversation continuity
            temperature: Optional model temperature
            max_tokens: Optional max tokens

        Yields:
            Event dictionaries from SSE stream
        """
        payload: dict[str, Any] = {"message": message}
        if thread_id:
            payload["thread_id"] = thread_id
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        async with self.client.stream(
            "POST",
            f"/api/v1/teams/{team_id}/stream",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        yield {"event": event_type, "data": data}
                    except json.JSONDecodeError:
                        # Skip invalid JSON
                        continue

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
