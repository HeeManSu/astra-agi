"""Registry module for agents, teams, and storage."""

from runtime.registry.registry import (
    AgentRegistry,
    StorageRegistry,
    TeamRegistry,
)


# Global registries
agent_registry = AgentRegistry()
team_registry = TeamRegistry()
storage_registry = StorageRegistry()

__all__ = [
    "AgentRegistry",
    "StorageRegistry",
    "TeamRegistry",
    "agent_registry",
    "storage_registry",
    "team_registry",
]
