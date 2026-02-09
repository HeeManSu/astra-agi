"""
MCP Toolkit - Thin wrapper around official mcp Python SDK.

Usage:
    async with MCPToolkit(command="npx", args=["-y", "@mcp/server-filesystem", "."]) as mcp:
        tools = await mcp.list_tools()
        result = await mcp.call_tool("read_file", path="/tmp/test.txt")
"""

from __future__ import annotations

from typing import Any


try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import get_default_environment, stdio_client
    from mcp.types import TextContent
except ImportError:
    raise ImportError("`mcp` package not installed. Install with: pip install mcp") from None


class MCPToolkit:
    """
    Minimal MCP toolkit using official SDK.

    Provides:
    - connect() - Connect to MCP server
    - list_tools() - Discover available tools
    - call_tool() - Execute a tool
    - close() - Cleanup connection
    """

    def __init__(
        self,
        name: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ):
        """
        Initialize MCP toolkit.

        Args:
            name: Identifier for this MCP server
            command: Command to run (e.g., "npx")
            args: Command arguments
            env: Additional environment variables
        """
        self.name = name
        self.command = command
        self.args = args or []
        self.env = {**get_default_environment(), **(env or {})}

        self._session: ClientSession | None = None
        self._context: Any = None
        self._session_context: Any = None

    async def connect(self) -> None:
        """Connect to the MCP server."""
        if self._session is not None:
            return

        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
        )

        # Use SDK's stdio_client
        self._context = stdio_client(server_params)
        read, write = await self._context.__aenter__()

        # Create session
        self._session_context = ClientSession(read, write)
        session = await self._session_context.__aenter__()
        self._session = session

        # Initialize protocol
        await session.initialize()

    async def list_tools(self) -> list[dict[str, Any]]:
        """
        Get available tools from the MCP server.

        Returns:
            List of tool definitions with name, description, inputSchema
        """
        if self._session is None:
            await self.connect()

        assert self._session is not None
        result = await self._session.list_tools()

        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": tool.inputSchema,
                "outputSchema": tool.outputSchema,
            }
            for tool in result.tools
        ]

    async def call_tool(self, name: str, **kwargs: Any) -> str:
        """
        Execute a tool on the MCP server.

        Args:
            name: Tool name
            **kwargs: Tool arguments

        Returns:
            Tool result as string
        """
        if self._session is None:
            await self.connect()

        assert self._session is not None
        result = await self._session.call_tool(name, kwargs)

        if result.isError:
            raise RuntimeError(f"MCP tool '{name}' failed: {result.content}")

        # Extract text content using list comprehension
        texts = [item.text for item in result.content if isinstance(item, TextContent)]

        return "\n".join(texts) if texts else str(result.content)

    async def close(self) -> None:
        """Close the MCP connection."""
        if self._session_context is not None:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception:
                pass

        if self._context is not None:
            try:
                await self._context.__aexit__(None, None, None)
            except Exception:
                pass

        self._session = None
        self._session_context = None
        self._context = None

    def get_tool_definitions(self, tool_definitions: dict[str, Any] | None) -> dict[str, Any]:
        """Filter tool definitions to return only tools belonging to this MCP."""
        if not tool_definitions:
            return {}

        expected_source = f"mcp:{self.name}"

        def matches_source(tool_def: Any) -> bool:
            """Check if tool definition source matches this MCP."""
            # Handle Pydantic models (attribute access)
            if hasattr(tool_def, "source"):
                return getattr(tool_def, "source", None) == expected_source
            # Handle dicts
            if isinstance(tool_def, dict):
                return tool_def.get("source") == expected_source
            return False

        return {
            tool_name: tool_def
            for tool_name, tool_def in tool_definitions.items()
            if matches_source(tool_def)
        }

    async def __aenter__(self) -> MCPToolkit:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"MCPToolkit(name='{self.name}', command='{self.command}')"
