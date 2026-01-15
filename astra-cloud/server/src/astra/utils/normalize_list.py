"""
Utility functions for normalizing agent and team lists to dictionaries.

This module provides utilities for converting lists of agents/teams into
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


def normalize_teams(teams: list[Any] | None) -> dict[str, Any]:
    """
    Normalize teams list to dictionary format.

    Converts a list of teams to a dictionary where keys are team IDs.
    If input is None or empty, returns empty dict.

    Args:
        teams: List of Team instances, or None

    Returns:
        Dictionary mapping team ID -> Team instance

    Examples:
        >>> teams = [team1, team2]
        >>> normalize_teams(teams)
        {'team1-id': team1, 'team2-id': team2}
    """
    if teams is None:
        return {}

    if not isinstance(teams, list):
        raise TypeError(f"Invalid teams type: {type(teams).__name__}. Expected list[Team] or None.")

    if not teams:
        return {}

    result: dict[str, Any] = {}
    for team in teams:
        if not hasattr(team, "id"):
            raise AttributeError(
                f"Team {type(team).__name__} does not have an 'id' attribute. "
                "All teams must have an 'id' to be normalized."
            )

        if not team.id:
            raise ValueError(
                f"Team {type(team).__name__} has an empty 'id' attribute. "
                "All teams must have a non-empty 'id' to be normalized."
            )

        team_id = str(team.id)

        # Handle duplicate IDs by appending index
        if team_id in result:
            base_id = team_id
            counter = 1
            while f"{base_id}-{counter}" in result:
                counter += 1
            team_id = f"{base_id}-{counter}"

        result[team_id] = team

    return result
