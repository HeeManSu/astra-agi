"""
MCP (Model Context Protocol) support for Astra.

Uses official mcp Python SDK for protocol handling.

Usage:
    from framework.tool.mcp import presets, MCPToolkit

    async with presets.filesystem(".") as mcp:
        tools = await mcp.list_tools()
        result = await mcp.call_tool("read_file", path="README.md")
"""

from framework.tool.mcp import presets
from framework.tool.mcp.toolkit import MCPToolkit


__all__ = [
    "MCPToolkit",
    "presets",
]
