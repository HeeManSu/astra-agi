"""
Tool Registry for Code Execution Mode.

Simple storage layer that maps qualified tool names ("agent_id.tool_name")
to Tool objects for lookup and execution in the sandbox.

Flow:
    Team.flat_members → ToolRegistry → Sandbox._handle_tool_call()
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from framework.tool import Tool


class ToolRegistry:
    """Maps qualified tool names to Tool objects.

    Provides a simple lookup interface for tool execution in code mode.
    Tools are stored as "agent_id.tool_name" to prevent name collisions.

    Usage:
        registry = ToolRegistry()
        registry.register("market_analyst", get_stock_price_tool)

        # Later, in sandbox:
        tool = registry.get("market_analyst.get_stock_price")
        result = tool.invoke(**args)
    """

    def __init__(self):
        """Initialize empty registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, agent_id: str, tool: Tool) -> None:
        """Register a tool under an agent namespace.

        Args:
            agent_id: Agent identifier (e.g., "market_analyst")
            tool: Tool instance to register

        Raises:
            ValueError: If tool with same qualified name already exists
        """
        qualified_name = f"{agent_id}.{tool.name}"
        if qualified_name in self._tools:
            raise ValueError(f"Tool '{qualified_name}' already registered")
        self._tools[qualified_name] = tool

    def get(self, qualified_name: str) -> Tool | None:
        """Look up tool by qualified name.

        Args:
            qualified_name: Full tool name (e.g., "market_analyst.get_stock_price")

        Returns:
            Tool if found, None otherwise
        """
        return self._tools.get(qualified_name)

    def list_tools(self) -> list[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)

    def __contains__(self, qualified_name: str) -> bool:
        """Check if tool exists (supports 'in' operator)."""
        return qualified_name in self._tools

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ToolRegistry(tools={len(self._tools)})"
