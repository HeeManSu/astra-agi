"""
MCPServer wrapper.
"""

from typing import Any

from framework.agents.tool import Tool, _sanitize_schema
from framework.mcp.client import MCPClient
from framework.mcp.transport import HTTPTransport, StdioTransport


class MCPServer:
    """
    Wraps an MCP Client with configuration and lifecycle management.
    """

    def __init__(
        self,
        name: str,
        command: str | None = None,
        args: list[str] | None = None,
        url: str | None = None,
        env: dict[str, str] | None = None,
    ):
        """
        Initialize MCPServer.

        Args:
            name: Server name
            command: Command to execute (for stdio)
            args: Command arguments
            url: URL (for HTTP)
            env: Environment variables
        """
        self.name = name
        self.command = command
        self.args = args or []
        self.url = url
        self.env = env
        self.client: MCPClient | None = None

    async def start(self) -> None:
        """Start server and connect."""
        if self.client:
            return

        if self.command:
            transport = StdioTransport(self.command, self.args, self.env)
        elif self.url:
            transport = HTTPTransport(self.url)
        else:
            raise ValueError("Either 'command' or 'url' must be provided")

        self.client = MCPClient(transport, self.name)
        await self.client.connect()

    async def stop(self) -> None:
        """Stop server and disconnect."""
        if self.client:
            await self.client.close()
            self.client = None

    async def get_tools(self) -> list[Tool]:
        """
        Get Astra-compatible tools from this server.

        Returns:
            List of Tool objects
        """
        if not self.client:
            await self.start()

        if not self.client:
            raise RuntimeError(f"Failed to start MCP server '{self.name}'")

        # client.list_tools() ensures connection
        mcp_tools = await self.client.list_tools()
        return self._convert_tools(mcp_tools)

    def _convert_tools(self, mcp_tools: list[dict[str, Any]]) -> list[Tool]:
        """Convert MCP tool definitions to Astra Tools."""
        astra_tools = []

        for tool_def in mcp_tools:
            name = tool_def["name"]
            description = tool_def.get("description", "")
            schema = tool_def.get("inputSchema", {})

            # Ensure schema has required structure (type, properties, required)
            # MCP inputSchema should already be a JSON Schema, but ensure it's properly formatted
            if not schema:
                schema = {"type": "object", "properties": {}, "required": []}
            elif "type" not in schema:
                # If no type specified, assume object type for tool parameters
                schema = {"type": "object", **schema}

            # Create a wrapper function that calls the MCP client
            # We use a factory to capture the variable 'name' correctly in the closure

            # Better approach:
            def create_wrapper(t_name: str):
                async def wrapper(**kwargs):
                    if not self.client:
                        raise RuntimeError(f"MCP Server '{self.name}' is not connected")
                    return await self.client.call_tool(t_name, kwargs)

                return wrapper

            func = create_wrapper(name)

            # Create Astra Tool
            # We manually inject the schema cache because Tool() usually infers it from the function
            tool_obj = Tool(name=name, description=description, func=func)
            # Sanitize and store the schema to remove $schema and other unsupported fields
            tool_obj._schema_cache = _sanitize_schema(schema)

            astra_tools.append(tool_obj)

        return astra_tools
