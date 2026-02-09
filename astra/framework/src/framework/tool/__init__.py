"""
Tool module for Astra Framework.

Tools are first-class citizens - independent of agents, teams, and runtime.

Core:
- Tool, bind_tool: Create tools from Python functions
- ToolSpec: Declarative tool specification

Note: ToolRegistry and ToolSync are in runtime package.
"""

from framework.tool.tool import Tool, bind_tool
from framework.tool.tool_spec import ToolSpec


__all__ = [
    "Tool",
    "ToolSpec",
    "bind_tool",
]
