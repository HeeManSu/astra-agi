"""
MCP Manager for orchestrating multiple servers.
"""

from __future__ import annotations

from typing import Any

from framework.agents.tool import Tool
from framework.mcp.registry import MCPRegistry
from framework.mcp.server import MCPServer


class MCPManager:
    """
    Manager for orchestrating multiple MCP servers.
    """

    def __init__(self):
        self.servers: list[MCPServer] = []

    async def add_server(
        self, name_or_server: str | MCPServer, config: dict[str, Any] | None = None
    ) -> None:
        """
        Add an MCP server.

        Args:
            name_or_server: Either a preset name (str) or an MCPServer instance
            config: Configuration dict if using a preset name
        """
        if isinstance(name_or_server, MCPServer):
            self.servers.append(name_or_server)
        elif isinstance(name_or_server, str):
            # Lookup in registry
            server = MCPRegistry.get(name_or_server, config or {})
            self.servers.append(server)
        else:
            raise ValueError("Argument must be a string (preset name) or MCPServer instance")

    async def get_tools(self) -> list[Tool]:
        """
        Start all servers and get aggregated tools.

        Returns:
            List of all tools from all servers
        """
        all_tools = []

        for server in self.servers:
            # This will start the server if needed
            tools = await server.get_tools()

            # TODO: Handle name collisions here if needed
            # For now, we just aggregate
            all_tools.extend(tools)

        return all_tools

    async def stop(self) -> None:
        """Stop all servers."""
        for server in self.servers:
            await server.stop()

    async def __aenter__(self) -> MCPManager:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
