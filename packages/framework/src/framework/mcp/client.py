"""
MCP client for connecting to MCP servers.
"""

from typing import Any

from framework.mcp.exceptions import MCPConnectionError, MCPToolExecutionError
from framework.mcp.transport import MCPTransport


class MCPClient:
    """
    MCP client for connecting to MCP servers.

    Handles:
    - Connection lifecycle
    - Tool discovery
    - Tool execution
    """

    def __init__(self, transport: MCPTransport, name: str = "mcp-server"):
        """
        Initialize MCP client.

        Args:
            transport: Transport layer (stdio or HTTP)
            name: Server name for logging
        """
        self.transport = transport
        self.name = name
        self.connected = False
        self.tools_cache: list[dict[str, Any]] | None = None

    async def connect(self) -> None:
        """Connect to MCP server and initialize."""
        try:
            await self.transport.connect()

            # Initialize connection
            # We ignore the result for now as we just need to establish the session
            await self.transport.send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "astra", "version": "1.0.0"},
                },
            )

            # Send initialized notification (optional but recommended by spec)
            try:
                await self.transport.send_request("notifications/initialized", {})
            except Exception:
                # Some servers might not support this or treat it as notification
                pass

            self.connected = True

        except Exception as e:
            raise MCPConnectionError(f"Failed to connect to MCP server '{self.name}': {e}") from e

    async def _ensure_connected(self) -> None:
        """Ensure connection is active."""
        if not self.connected:
            await self.connect()

    async def list_tools(self) -> list[dict[str, Any]]:
        """
        Fetch available tools from MCP server.

        Returns:
            List of tool definitions in MCP format
        """
        await self._ensure_connected()

        try:
            result = await self.transport.send_request("tools/list", {})
            self.tools_cache = result.get("tools", [])
            return self.tools_cache or []

        except Exception as e:
            raise MCPConnectionError(f"Failed to list tools from '{self.name}': {e}") from e

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """
        Execute tool on MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        await self._ensure_connected()

        try:
            result = await self.transport.send_request(
                "tools/call", {"name": name, "arguments": arguments}
            )

            return result

        except Exception as e:
            raise MCPToolExecutionError(f"Tool '{name}' execution failed: {e}") from e

    async def close(self) -> None:
        """Close connection to MCP server."""
        await self.transport.close()
        self.connected = False
