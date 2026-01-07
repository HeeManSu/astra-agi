"""
Utility functions for normalizing agent lists to dictionaries.

This module provides utilities for converting lists of agents into
the dictionary format required by the registry and server.
"""

from typing import Any


def normalize_agents(agents: list[Any] | None) -> dict[str, Any]:
    """
    Normalize agents list to dictionary format.

    Converts a list of agents to a dictionary where keys are agent IDs.
    If input is None or empty, returns empty dict.

    Args:
        agents: List of Agent instances, or None

    Returns:
        Dictionary mapping agent ID -> Agent instance

    Examples:
        >>> agents = [agent1, agent2]
        >>> normalize_agents(agents)
        {'agent1-id': agent1, 'agent2-id': agent2}
    """
    if agents is None:
        return {}

    if not isinstance(agents, list):
        raise TypeError(
            f"Invalid agents type: {type(agents).__name__}. Expected list[Agent] or None."
        )

    if not agents:
        return {}

    result: dict[str, Any] = {}
    for agent in agents:
        if not hasattr(agent, "id"):
            raise AttributeError(
                f"Agent {type(agent).__name__} does not have an 'id' attribute. "
                "All agents must have an 'id' to be normalized."
            )

        if not agent.id:
            raise ValueError(
                f"Agent {type(agent).__name__} has an empty 'id' attribute. "
                "All agents must have a non-empty 'id' to be normalized."
            )

        agent_id = str(agent.id)

        # Handle duplicate IDs by appending index
        if agent_id in result:
            base_id = agent_id
            counter = 1
            while f"{base_id}-{counter}" in result:
                counter += 1
            agent_id = f"{base_id}-{counter}"

        result[agent_id] = agent

    return result
