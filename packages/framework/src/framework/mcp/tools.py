"""
MCPTools - Simplified MCP integration for Astra.

Provides easy-to-use wrapper for MCP tool integration.
"""
from typing import Any, Callable, Dict, List, Optional

from .client import MCPClient
from .transport import StdioTransport, HTTPTransport
from .exceptions import MCPError, MCPConnectionError


class MCPTools:
    """
    Simplified MCP tools integration.
    
    Auto-initializes on first use, handles collision detection,
    and provides clean developer experience.
    
    Example:
        ```python
        from framework.mcp import MCPTools
        from framework.agents import Agent
        
        mcp = MCPTools(
            command="npx -y @modelcontextprotocol/server-filesystem .",
            prefix="fs"  # optional
        )
        
        agent = Agent(
            name="FileAgent",
            model="gpt-4o-mini",
            tools=[mcp]
        )
        
        # MCP tools auto-initialize on first run
        result = await agent.run("Read utils.py")
        ```
    """
    
    def __init__(
        self,
        command: Optional[str] = None,
        url: Optional[str] = None,
        prefix: Optional[str] = None,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        name: str = "mcp-server"
    ):
        """
        Initialize MCP tools.
        
        Args:
            command: Command to run MCP server (stdio transport)
            url: URL for HTTP MCP server
            prefix: Optional prefix for tool names (e.g., "fs_")
            include: Only include these tools
            exclude: Exclude these tools
            name: Server name for logging
            
        Example:
            ```python
            # Stdio transport
            mcp = MCPTools(command="npx -y @modelcontextprotocol/server-filesystem .")
            
            # HTTP transport
            mcp = MCPTools(url="https://api.example.com/mcp")
            
            # With prefix
            mcp = MCPTools(command="...", prefix="fs")
            ```
        """
        if not command and not url:
            raise ValueError("Either 'command' or 'url' must be provided")
        
        if command and url:
            raise ValueError("Provide either 'command' or 'url', not both")
        
        self.command = command
        self.url = url
        self.prefix = prefix
        self.include = include
        self.exclude = exclude or []
        self.name = name
        
        # Internal state
        self._client: Optional[MCPClient] = None
        self._tools: Optional[List[Any]] = None
        self._initialized = False
    
    async def initialize(self, existing_tool_names: Optional[List[str]] = None) -> List[Any]:
        """
        Initialize MCP client and fetch tools.
        
        Args:
            existing_tool_names: List of existing tool names for collision detection
            
        Returns:
            List of Astra Tool instances
        """
        if self._initialized and self._tools:
            return self._tools
        
        # Create transport
        if self.command:
            # Parse command
            parts = self.command.split()
            cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            transport = StdioTransport(cmd, args)
        else:
            transport = HTTPTransport(self.url)  # type: ignore
        
        # Create client
        self._client = MCPClient(transport, name=self.name)
        
        # Connect and fetch tools
        await self._client.connect()
        mcp_tools = await self._client.list_tools()
        
        # Detect collisions and auto-add prefix if needed
        final_prefix = self._detect_collisions(mcp_tools, existing_tool_names)
        
        # Convert to Astra tools
        self._tools = self._convert_tools(mcp_tools, final_prefix)
        self._initialized = True
        
        return self._tools
    
    def _detect_collisions(
        self,
        mcp_tools: List[Dict[str, Any]],
        existing_tool_names: Optional[List[str]]
    ) -> str:
        """
        Detect name collisions and determine final prefix.
        
        Args:
            mcp_tools: MCP tool definitions
            existing_tool_names: Existing tool names
            
        Returns:
            Final prefix to use
        """
        if self.prefix is not None:
            # User explicitly set prefix
            return self.prefix
        
        if not existing_tool_names:
            # No existing tools, no collision possible
            return ""
        
        # Check for collisions
        mcp_tool_names = {tool["name"] for tool in mcp_tools}
        collisions = mcp_tool_names & set(existing_tool_names)
        
        if collisions:
            # Auto-add prefix based on server name
            auto_prefix = f"{self.name}_"
            return auto_prefix
        
        return ""
    
    def _convert_tools(
        self,
        mcp_tools: List[Dict[str, Any]],
        prefix: str
    ) -> List[Any]:
        """
        Convert MCP tools to Astra Tool format.
        
        Args:
            mcp_tools: MCP tool definitions
            prefix: Prefix for tool names
            
        Returns:
            List of Astra Tool instances
        """
        from ..agents.tool import Tool
        
        astra_tools = []
        
        for mcp_tool in mcp_tools:
            tool_name = mcp_tool["name"]
            
            # Apply filters
            if self.include and tool_name not in self.include:
                continue
            if tool_name in self.exclude:
                continue
            
            # Add prefix
            final_name = f"{prefix}{tool_name}" if prefix else tool_name
            
            # Create execution wrapper
            async def execute_mcp_tool(**kwargs):
                if not self._client:
                    raise MCPError("MCP client not initialized")
                
                # Extract original tool name from closure
                original_name = mcp_tool["name"]
                
                try:
                    result = await self._client.call_tool(original_name, kwargs)
                    return result
                except Exception as e:
                    # Return error via tool_result (don't raise)
                    return {"error": str(e), "success": False}
            
            # Create Astra tool
            astra_tool = Tool(
                name=final_name,
                description=mcp_tool.get("description", ""),
                parameters=mcp_tool.get("inputSchema", {}),
                invoke=execute_mcp_tool
            )
            
            astra_tools.append(astra_tool)
        
        return astra_tools
    
    async def close(self) -> None:
        """Close MCP client connection."""
        if self._client:
            await self._client.close()
            self._initialized = False
