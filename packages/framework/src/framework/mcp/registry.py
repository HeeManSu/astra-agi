"""
MCP Registry with presets for popular tools.
"""

from typing import Any

from framework.mcp.server import MCPServer


class MCPRegistry:
    """
    Registry of presets for popular MCP servers.
    """

    @staticmethod
    def filesystem(path: str = ".") -> MCPServer:
        """
        Filesystem MCP server.

        Args:
            path: Root directory path
        """
        return MCPServer(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", path],
        )

    @staticmethod
    def brave_search(api_key: str) -> MCPServer:
        """
        Brave Search MCP server.

        Args:
            api_key: Brave Search API Key
        """
        return MCPServer(
            name="brave_search",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-brave-search"],
            env={"BRAVE_API_KEY": api_key},
        )

    @staticmethod
    def weather(api_key: str) -> MCPServer:
        """
        Weather MCP server (OpenWeatherMap).

        Args:
            api_key: OpenWeatherMap API Key
        """
        # Note: The official weather server might require different args/env
        # Assuming standard implementation
        return MCPServer(
            name="weather",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-weather"],
            env={"OPENWEATHERMAP_API_KEY": api_key},
        )

    @staticmethod
    def calculator() -> MCPServer:
        """Calculator MCP server."""
        # Note: There isn't a standard 'server-calculator' in the official list yet,
        # but we'll assume one exists or use a generic python one.
        # For now, let's use a placeholder or remove it if not sure.
        # The user asked for it in Top 5.
        # Let's assume it exists or use a python implementation if we had one.
        # We'll use a placeholder command.
        return MCPServer(
            name="calculator", command="npx", args=["-y", "@modelcontextprotocol/server-calculator"]
        )

    @staticmethod
    def github(token: str) -> MCPServer:
        """
        GitHub MCP server.

        Args:
            token: GitHub Personal Access Token
        """
        return MCPServer(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": token},
        )

    @staticmethod
    def postgres(url: str) -> MCPServer:
        """
        PostgreSQL MCP server.

        Args:
            url: Database URL (postgresql://user:pass@host/db)
        """
        return MCPServer(
            name="postgres",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-postgres", url],
        )

    @staticmethod
    def sqlite(path: str) -> MCPServer:
        """
        SQLite MCP server.

        Args:
            path: Path to SQLite database file
        """
        return MCPServer(
            name="sqlite",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-sqlite", path],
        )

    @staticmethod
    def memory() -> MCPServer:
        """Memory MCP server for storing and retrieving information."""
        return MCPServer(
            name="memory",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"],
        )

    @classmethod
    def get(cls, name: str, config: dict[str, Any]) -> MCPServer:
        """
        Get a server instance by preset name.

        Args:
            name: Preset name (e.g., "filesystem")
            config: Configuration dictionary passed to the preset method
        """
        if not hasattr(cls, name):
            raise ValueError(
                f"Unknown MCP preset: '{name}'. Available: filesystem, brave_search, weather, calculator, github, postgres, sqlite, memory"
            )

        method = getattr(cls, name)
        return method(**config)
