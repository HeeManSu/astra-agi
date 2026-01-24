"""
CodeModeProvider Protocol for Astra.

This module defines the interface that any entity (Agent, Team, Workflow, etc.)
must implement to be compatible with the Code Mode Sandbox.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable


if TYPE_CHECKING:
    from framework.code_mode.semantic import EntitySemanticLayer
    from framework.code_mode.tool_registry import ToolRegistry
    from framework.models.base import Model


@runtime_checkable
class CodeModeProvider(Protocol):
    """
    Protocol for entities that provide tools and metadata for Code Mode.

    Any object that implements this protocol can be used directly with the Sandbox.
    """

    model: Model

    @property
    def provider_type(self) -> str:
        """Type identifier (e.g., 'TEAM', 'AGENT', 'WORKFLOW')."""
        ...

    @property
    def semantic_layer(self) -> EntitySemanticLayer:
        """
        Structured representation of the entity's tools for stub generation.
        """
        ...

    @property
    def tool_registry(self) -> ToolRegistry:
        """
        Mapping of tool names to executable Tool objects.
        """
        ...

    async def get_history(self, thread_id: str) -> list[dict[str, Any]]:
        """
        Retrieve conversation history for a given thread.

        Args:
            thread_id: Unique identifier for the conversation thread.

        Returns:
            List of message dictionaries (role, content).
        """
        ...
