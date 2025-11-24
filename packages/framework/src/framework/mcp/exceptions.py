"""
MCP exceptions.
"""


class MCPError(Exception):
    """Base exception for MCP errors."""
    pass


class MCPConnectionError(MCPError):
    """Failed to connect to MCP server."""
    pass


class MCPToolExecutionError(MCPError):
    """Tool execution failed on MCP server."""
    pass


class MCPSchemaConversionError(MCPError):
    """Schema conversion failed."""
    pass


class MCPTransportError(MCPError):
    """Transport layer error."""
    pass
