"""
MCP client for connecting to MCP servers.
"""
import asyncio
from typing import Any, Dict, List, Optional

from .transport import MCPTransport
from .exceptions import MCPConnectionError, MCPToolExecutionError


class MCPClient:
    """
    MCP client for connecting to MCP servers.
    
    Handles:
    - Connection lifecycle with auto-reconnect
    - Tool discovery
    - Tool execution
    - Error handling
    
    Example:
        ```python
        from framework.mcp.transport import StdioTransport
        
        transport = StdioTransport("npx", ["-y", "@modelcontextprotocol/server-filesystem", "."])
        client = MCPClient(transport)
        
        await client.connect()
        tools = await client.list_tools()
        result = await client.call_tool("read_file", {"path": "test.txt"})
        ```
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
        self.tools_cache: Optional[List[Dict[str, Any]]] = None
        self._retry_count = 0
        self._max_retries = 1  # Retry once automatically
    
    async def connect(self) -> None:
        """Connect to MCP server and initialize."""
        try:
            await self.transport.connect()
            
            # Initialize connection
            result = await self.transport.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "astra",
                    "version": "1.0.0"
                }
            })
            
            self.connected = True
            self._retry_count = 0
        
        except Exception as e:
            raise MCPConnectionError(f"Failed to connect to MCP server '{self.name}': {e}")
    
    async def _ensure_connected(self) -> None:
        """Ensure connection is active, reconnect if needed."""
        if not self.connected:
            await self.connect()
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect to MCP server."""
        if self._retry_count >= self._max_retries:
            raise MCPConnectionError(
                f"Failed to reconnect to MCP server '{self.name}' after {self._max_retries} attempts"
            )
        
        self._retry_count += 1
        await self.close()
        await asyncio.sleep(0.5)  # Brief delay before retry
        await self.connect()
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Fetch available tools from MCP server.
        
        Returns:
            List of tool definitions in MCP format
            
        Raises:
            MCPConnectionError: If connection fails
        """
        await self._ensure_connected()
        
        try:
            result = await self.transport.send_request("tools/list", {})
            self.tools_cache = result.get("tools", [])
            return self.tools_cache or []
        
        except Exception as e:
            # Try to reconnect once
            try:
                await self._reconnect()
                result = await self.transport.send_request("tools/list", {})
                self.tools_cache = result.get("tools", [])
                return self.tools_cache or []
            except Exception:
                raise MCPConnectionError(f"Failed to list tools from '{self.name}': {e}")
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute tool on MCP server.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            MCPToolExecutionError: If tool execution fails
        """
        await self._ensure_connected()
        
        try:
            result = await self.transport.send_request("tools/call", {
                "name": name,
                "arguments": arguments
            })
            
            return result
        
        except Exception as e:
            # For tool execution failures, return error (don't auto-reconnect)
            # This allows the model to retry if needed
            raise MCPToolExecutionError(f"Tool '{name}' execution failed: {e}")
    
    async def close(self) -> None:
        """Close connection to MCP server."""
        await self.transport.close()
        self.connected = False
