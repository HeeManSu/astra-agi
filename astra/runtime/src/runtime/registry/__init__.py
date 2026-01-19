"""Registry module for agents and teams."""

from runtime.registry.registry import AgentRegistry, TeamRegistry


# Global registries
agent_registry = AgentRegistry()
team_registry = TeamRegistry()

__all__ = [
    "AgentRegistry",
    "TeamRegistry",
    "agent_registry",
    "team_registry",
]
