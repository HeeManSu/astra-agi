"""
Built-in MCP servers for common use cases.
"""
from typing import Optional
from .tools import MCPTools


class FilesystemMCP:
    """
    Filesystem MCP server.
    
    Tools:
    - read_file: Read file contents
    - write_file: Write to file
    - list_directory: List directory contents
    - create_directory: Create directory
    - move_file: Move/rename file
    - search_files: Search for files
    
    Example:
        ```python
        from framework.mcp.builtin import FilesystemMCP
        
        mcp = FilesystemMCP.create(root_path=".")
        
        agent = Agent(
            name="FileAgent",
            model="gpt-4o-mini",
            tools=[mcp]
        )
        ```
    """
    
    @staticmethod
    def create(root_path: str = ".", prefix: Optional[str] = None) -> MCPTools:
        """
        Create filesystem MCP tools.
        
        Args:
            root_path: Root directory path
            prefix: Optional prefix for tool names
            
        Returns:
            MCPTools instance
        """
        return MCPTools(
            command=f"npx -y @modelcontextprotocol/server-filesystem {root_path}",
            prefix=prefix,
            name="filesystem"
        )


class CalculatorMCP:
    """
    Calculator MCP server for safe math operations.
    
    Tools:
    - calculate: Evaluate mathematical expressions safely
    
    Example:
        ```python
        from framework.mcp.builtin import CalculatorMCP
        
        mcp = CalculatorMCP.create()
        
        agent = Agent(
            name="MathAgent",
            model="gpt-4o-mini",
            tools=[mcp]
        )
        ```
    """
    
    @staticmethod
    def create(prefix: Optional[str] = None) -> MCPTools:
        """
        Create calculator MCP tools.
        
        Args:
            prefix: Optional prefix for tool names
            
        Returns:
            MCPTools instance
        """
        # Note: This assumes a calculator MCP server is available
        # You may need to install it separately or create a simple one
        return MCPTools(
            command="npx -y @modelcontextprotocol/server-everything",
            prefix=prefix,
            name="calculator",
            include=["calculate"]  # Only include calculator tool
        )


class WebSearchMCP:
    """
    Web search MCP server using Brave Search.
    
    Tools:
    - brave_web_search: Search the web using Brave Search
    
    Requires BRAVE_API_KEY environment variable.
    
    Example:
        ```python
        from framework.mcp.builtin import WebSearchMCP
        
        mcp = WebSearchMCP.create()
        
        agent = Agent(
            name="SearchAgent",
            model="gpt-4o-mini",
            tools=[mcp]
        )
        ```
    """
    
    @staticmethod
    def create(prefix: Optional[str] = None) -> MCPTools:
        """
        Create web search MCP tools.
        
        Args:
            prefix: Optional prefix for tool names
            
        Returns:
            MCPTools instance
        """
        return MCPTools(
            command="npx -y @modelcontextprotocol/server-brave-search",
            prefix=prefix,
            name="web-search"
        )
