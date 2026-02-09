"""
Lazy per-agent tool cache.

Fetches tool definitions from DB on first request per agent/team,
caches for subsequent requests.

Flow:
    Route → get_agent_tool_definitions(agent_id) → Cache hit? → Return
                                                  → Cache miss? → Fetch from DB → Cache → Return
"""

from typing import TYPE_CHECKING, Any

from framework.storage.models import ToolDefinition
from framework.tool import Tool
from framework.tool.mcp.toolkit import MCPToolkit


if TYPE_CHECKING:
    pass

# Separate caches for agents and teams
_agent_cache: dict[str, dict[str, ToolDefinition]] = {}
_team_cache: dict[str, dict[str, ToolDefinition]] = {}


def _build_tool_slugs(tools: list[Any]) -> list[str]:
    """Build slugs for local tools."""
    return [
        f"local-{t.name}".lower().replace("_", "-") for t in (tools or []) if isinstance(t, Tool)
    ]


def _get_mcp_sources(tools: list[Any]) -> list[str]:
    """Get MCP source names from tools."""
    return [f"mcp:{t.name}" for t in (tools or []) if isinstance(t, MCPToolkit)]


async def get_agent_tool_definitions(agent_id: str) -> dict[str, ToolDefinition]:
    """
    Get tool definitions for an agent (lazy-loaded from DB).

    Returns:
        Dict mapping slug to ToolDefinition
    """
    if agent_id in _agent_cache:
        return _agent_cache[agent_id]

    from framework.storage.stores.tool_definition import ToolDefinitionStore

    from runtime.registry import agent_registry, storage_registry

    storage = storage_registry.get_default()
    if not storage:
        return {}

    agent = agent_registry.get(agent_id)
    if not agent:
        return {}

    tools = agent.tools or []
    local_slugs = _build_tool_slugs(tools)
    mcp_sources = _get_mcp_sources(tools)

    store: ToolDefinitionStore = ToolDefinitionStore(storage.storage)
    result: dict[str, ToolDefinition] = {}

    if local_slugs:
        local_defs = await store.get_by_slugs(local_slugs)
        result.update(local_defs)

    if mcp_sources:
        mcp_defs = await store.get_by_sources(mcp_sources)
        result.update({d.slug: d for d in mcp_defs})

    _agent_cache[agent_id] = result
    return _agent_cache[agent_id]


async def get_team_tool_definitions(team_id: str) -> dict[str, ToolDefinition]:
    """
    Get tool definitions for a team (lazy-loaded from DB).

    Returns:
        Dict mapping slug to ToolDefinition
    """
    if team_id in _team_cache:
        return _team_cache[team_id]

    from framework.storage.stores.tool_definition import ToolDefinitionStore

    from runtime.registry import storage_registry, team_registry

    storage = storage_registry.get_default()
    if not storage:
        return {}

    team = team_registry.get(team_id)
    if not team:
        return {}

    # Collect tools from all team members
    all_tools: list[Any] = []
    for member in team.members or []:
        agent = getattr(member, "agent", member)
        all_tools.extend(getattr(agent, "tools", []) or [])

    local_slugs = _build_tool_slugs(all_tools)
    mcp_sources = _get_mcp_sources(all_tools)

    store: ToolDefinitionStore = ToolDefinitionStore(storage.storage)
    result: dict[str, ToolDefinition] = {}

    if local_slugs:
        local_defs = await store.get_by_slugs(local_slugs)
        result.update(local_defs)

    if mcp_sources:
        mcp_defs = await store.get_by_sources(mcp_sources)
        result.update({d.slug: d for d in mcp_defs})

    _team_cache[team_id] = result
    return _team_cache[team_id]


def invalidate_agent_cache(agent_id: str | None = None) -> None:
    """Invalidate agent cache."""
    if agent_id:
        _agent_cache.pop(agent_id, None)
    else:
        _agent_cache.clear()


def invalidate_team_cache(team_id: str | None = None) -> None:
    """Invalidate team cache."""
    if team_id:
        _team_cache.pop(team_id, None)
    else:
        _team_cache.clear()
