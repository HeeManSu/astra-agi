"""
Tool Registry for Code Execution Mode.

This module provides a simple dict-based registry for organizing and querying
agent tools. It's the foundation for virtual API generation in Code Execution Mode.

Architecture:
    Agent Tools → Tool Registry (dict) → Virtual API Generator → astra_api.py → Sandbox
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from framework.agents.tool import Tool


@dataclass
class ToolSpec:
    """Specification for a tool (Python @tool or MCP tool).

    This is a lightweight wrapper around Tool instances that adds metadata
    for code generation and module organization.

    Attributes:
        name: Tool name (e.g., 'get_user' or 'crm.get_user')
        description: Tool description from docstring
        parameters: JSON Schema parameters
        invoke: Function to invoke the tool
        module: Module/namespace for grouping (e.g., 'crm', 'gdrive')
        is_mcp: True if this tool comes from an MCP server
        mcp_server_name: MCP server name if is_mcp=True
        metadata: Additional metadata for future extensions
    """

    name: str
    description: str
    parameters: dict[str, Any]
    invoke: Callable
    module: str = "default"
    is_mcp: bool = False
    mcp_server_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_tool(
        cls,
        tool: Tool,
        module: str = "default",
        is_mcp: bool = False,
        mcp_server_name: str | None = None,
    ) -> ToolSpec:
        """Create ToolSpec from existing Tool instance.

        Args:
            tool: Tool instance to convert
            module: Module/namespace for grouping
            is_mcp: Whether this is an MCP tool
            mcp_server_name: MCP server name if applicable

        Returns:
            ToolSpec instance
        """
        return cls(
            name=tool.name,
            description=tool.description,
            parameters=tool.parameters,
            invoke=tool,  # Store the Tool object itself (it's callable)
            module=module,
            is_mcp=is_mcp,
            mcp_server_name=mcp_server_name,
        )


class ToolRegistry:
    """Per-agent tool registry for organizing and querying tools.

    Each agent instance has its own ToolRegistry containing only the tools
    assigned to that agent. This ensures sandbox isolation - each agent's
    code execution sandbox can only access its own tools.

    The registry is essentially a Dict[str, ToolSpec] that provides:
    - Tool storage by name
    - Grouping by module/namespace
    - Filtering by type (MCP vs Python)
    - Query interface for virtual API generation

    Example:
        >>> registry = ToolRegistry(agent_id="my-agent")
        >>> registry.register(tool_spec)
        >>> tools = registry.list_tools()
        >>> grouped = registry.get_specs_grouped_by_module()
    """

    def __init__(self, agent_id: str):
        """Initialize registry for an agent.

        Args:
            agent_id: Agent identifier (e.g., agent.id or agent.name)
        """
        self.agent_id = agent_id
        self._tools: dict[str, ToolSpec] = {}

    def register(self, tool_spec: ToolSpec) -> None:
        """Register a tool.

        Args:
            tool_spec: Tool specification

        Raises:
            ValueError: If tool name already exists
        """
        if tool_spec.name in self._tools:
            raise ValueError(
                f"Tool '{tool_spec.name}' already registered for agent '{self.agent_id}'"
            )
        self._tools[tool_spec.name] = tool_spec

    def register_many(self, tool_specs: list[ToolSpec]) -> None:
        """Register multiple tools at once.

        Args:
            tool_specs: List of tool specifications
        """
        for spec in tool_specs:
            self.register(spec)

    def get(self, name: str) -> ToolSpec | None:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            ToolSpec if found, None otherwise
        """
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """Check if tool exists.

        Args:
            name: Tool name

        Returns:
            True if tool exists
        """
        return name in self._tools

    def list_tools(self) -> list[ToolSpec]:
        """List all tool specs.

        Returns:
            List of all ToolSpec instances
        """
        return list(self._tools.values())

    def list_tool_names(self) -> list[str]:
        """List all tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_by_module(self, module: str) -> list[ToolSpec]:
        """Get all tools in a module.

        Args:
            module: Module name (e.g., 'crm')

        Returns:
            List of ToolSpec instances in that module
        """
        return [spec for spec in self._tools.values() if spec.module == module]

    def get_specs_grouped_by_module(self) -> dict[str, list[ToolSpec]]:
        """Group tools by module for API generation.

        This is the primary method used by the Virtual API Generator to
        organize tools into namespaces.

        Returns:
            Dict mapping module name to list of ToolSpec instances

        Example:
            {
                'crm': [ToolSpec(name='get_user', ...), ToolSpec(name='update_user', ...)],
                'gdrive': [ToolSpec(name='get_document', ...)]
            }
        """
        grouped: dict[str, list[ToolSpec]] = defaultdict(list)
        for spec in self._tools.values():
            grouped[spec.module].append(spec)
        return dict(grouped)

    def get_mcp_tools(self) -> list[ToolSpec]:
        """Get all MCP tools.

        Returns:
            List of MCP ToolSpec instances
        """
        return [spec for spec in self._tools.values() if spec.is_mcp]

    def get_python_tools(self) -> list[ToolSpec]:
        """Get all Python @tool functions.

        Returns:
            List of Python ToolSpec instances
        """
        return [spec for spec in self._tools.values() if not spec.is_mcp]

    def clear(self) -> None:
        """Clear all tools from registry."""
        self._tools.clear()

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)

    def __repr__(self) -> str:
        return f"ToolRegistry(agent_id='{self.agent_id}', tools={len(self._tools)})"

    def __contains__(self, name: str) -> bool:
        """Check if tool exists using 'in' operator."""
        return name in self._tools
