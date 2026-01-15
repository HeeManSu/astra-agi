"""
MCP Exceptions.
"""


class MCPError(Exception):
    """Base exception for MCP errors."""


class MCPConnectionError(MCPError):
    """Raised when connection to MCP server fails."""


class MCPTransportError(MCPError):
    """Raised when transport communication fails."""


class MCPToolExecutionError(MCPError):
    """Raised when tool execution fails."""
