"""
Registry module for storing and retrieving agents and teams.

The registry pattern provides a centralized lookup mechanism for
registered components, enabling the API layer to resolve agent/team
identifiers to their corresponding instances.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar


if TYPE_CHECKING:
    from framework.agents import Agent
    from framework.team import Team


T = TypeVar("T")


class Registry(Generic[T]):
    """
    Generic registry for storing and retrieving items by ID.

    Provides a thread-safe mapping from string identifiers to instances.
    Subclasses must implement `_get_id` to define ID extraction logic.
    """

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def register(self, item: T) -> None:
        """Register an item in the registry."""
        item_id = self._get_id(item)
        self._items[item_id] = item

    def get(self, item_id: str) -> T | None:
        """Retrieve an item by ID. Returns None if not found."""
        return self._items.get(item_id)

    def list_all(self) -> list[T]:
        """Return all registered items."""
        return list(self._items.values())

    def _get_id(self, item: T) -> str:
        """Extract the ID from an item. Must be implemented by subclasses."""
        raise NotImplementedError


class AgentRegistry(Registry["Agent"]):
    """Registry for Agent instances."""

    def _get_id(self, agent: Agent) -> str:
        return agent.id or agent.name


class TeamRegistry(Registry["Team"]):
    """Registry for Team instances."""

    def _get_id(self, team: Team) -> str:
        return team.id or team.name


class StorageRegistry:
    """Registry for storage backends."""

    def __init__(self) -> None:
        self._default: Any | None = None

    def set_default(self, storage: Any) -> None:
        """Set the default storage backend."""
        self._default = storage

    def get_default(self) -> Any | None:
        """Get the default storage backend."""
        return self._default
