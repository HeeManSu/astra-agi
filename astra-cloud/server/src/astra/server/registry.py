"""
Astra Server Registry.

Central registry for agents and discovered resources.
Handles auto-discovery of storage, MCP tools, and RAG pipelines.
"""

from dataclasses import dataclass, field
import logging
from typing import Any

from framework.storage.memory import AgentStorage


logger = logging.getLogger(__name__)


@dataclass
class StorageInfo:
    """Information about a discovered storage backend."""

    id: str
    instance: Any
    type_name: str
    used_by: list[str] = field(default_factory=list)


@dataclass
class AgentRegistry:
    """
    Central registry for all server resources.

    Provides single source of truth for:
    - Registered agents
    - Registered teams
    - Discovered storage backends (deduplicated)
    - Discovered MCP tools
    - Discovered RAG pipelines
    """

    agents: dict[str, Any] = field(default_factory=dict)
    teams: dict[str, Any] = field(default_factory=dict)
    storage: dict[int, StorageInfo] = field(default_factory=dict)
    mcp_tools: list[Any] = field(default_factory=list)
    rag_pipelines: list[Any] = field(default_factory=list)

    def get_agent(self, agent_id: str) -> Any | None:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def get_team(self, team_id: str) -> Any | None:
        """Get team by ID."""
        return self.teams.get(team_id)

    def list_agent_names(self) -> list[str]:
        """List all agent IDs (registry keys)."""
        return list(self.agents.keys())

    def list_team_names(self) -> list[str]:
        """List all team IDs (registry keys)."""
        return list(self.teams.keys())

    def get_storage_for_agent(self, agent_id: str) -> Any | None:
        """Get storage backend used by an agent."""
        for storage_info in self.storage.values():
            if agent_id in storage_info.used_by:
                return storage_info.instance
        return None


def validate_agents(agents: dict[str, Any]) -> None:
    """
    Validate agents dictionary.

    Raises:
        ValueError: If no agents provided or invalid agents detected
    """
    if not agents:
        raise ValueError(
            "No agents registered. Pass at least one agent: create_app(agents={'my-agent': agent})"
        )

    # Check for None values
    for agent_id, agent in agents.items():
        if agent is None:
            raise ValueError(
                f"Agent '{agent_id}' is None. Make sure to pass an Agent instance, not None."
            )

    # Check agent has required attributes
    for agent_id, agent in agents.items():
        if not hasattr(agent, "invoke"):
            raise ValueError(
                f"Agent '{agent_id}' is not a valid Agent instance. "
                f"Expected object with 'invoke' method, got {type(agent).__name__}."
            )

    logger.info(f"Validated {len(agents)} agents: {list(agents.keys())}")


def discover_all(
    agents: dict[str, Any],
    global_storage: Any | None = None,
) -> dict[str, Any]:
    """
    Discover all resources from agents.

    Args:
        agents: Dict of agent ID -> Agent instance
        global_storage: Optional global storage to apply as fallback

    Returns:
        Dict with discovered resources:
        - storage: Dict[id, StorageInfo]
        - mcp_tools: List[MCPServer]
        - rag_pipelines: List[Rag]
    """
    return {
        "storage": discover_storage(agents, global_storage),
        "mcp_tools": discover_mcp_tools(agents),
        "rag_pipelines": discover_rag_pipelines(agents),
    }


def discover_storage(
    agents: dict[str, Any],
    global_storage: Any | None = None,
) -> dict[int, StorageInfo]:
    """
    Discover unique storage backends from agents.

    Handles:
    - Per-agent storage
    - Shared storage (same instance - deduplicated by id())
    - Global storage fallback for agents without storage

    Args:
        agents: Dict of agent ID -> Agent instance
        global_storage: Optional global storage to apply as fallback

    Returns:
        Dict of instance_id -> StorageInfo (deduplicated)
    """
    discovered: dict[int, StorageInfo] = {}
    storage_count = 0

    # Apply global storage fallback
    if global_storage:
        for agent_id, agent in agents.items():
            if not hasattr(agent, "storage") or agent.storage is None:
                # Wrap raw storage backend in AgentStorage (API layer)
                # Match Agent.__init__ behavior: use memory.num_history_responses (default: 10)
                # Note: max_messages is just a retrieval hint; actual limit is controlled by
                # MemoryManager using window_size or token_limit. Messages are always stored
                # if storage exists, but only loaded into context if memory.add_history_to_messages=True
                max_messages = (
                    agent.memory.num_history_responses
                    if hasattr(agent, "memory") and hasattr(agent.memory, "num_history_responses")
                    else 10  # Match AgentMemory default
                )
                agent.storage = AgentStorage(
                    storage=global_storage,
                    max_messages=max_messages,
                )
                logger.debug(f"Applied global storage to agent: {agent_id}")

    # Discover unique instances
    for agent_id, agent in agents.items():
        if hasattr(agent, "storage") and agent.storage is not None:
            instance_id = id(agent.storage)

            if instance_id not in discovered:
                storage_id = f"storage-{storage_count}"
                storage_count += 1
                discovered[instance_id] = StorageInfo(
                    id=storage_id,
                    instance=agent.storage,
                    type_name=type(agent.storage).__name__,
                    used_by=[agent_id],
                )
                logger.info(
                    f"Discovered storage: {storage_id} "
                    f"({type(agent.storage).__name__}) for agent: {agent_id}"
                )
            else:
                discovered[instance_id].used_by.append(agent_id)
                logger.debug(f"Storage {discovered[instance_id].id} shared with agent: {agent_id}")

    if discovered:
        logger.info(f"Total unique storage backends: {len(discovered)}")
    else:
        logger.info("No storage backends discovered")

    return discovered


def discover_mcp_tools(agents: dict[str, Any]) -> list[Any]:
    """
    Discover MCP tools from agents.

    Args:
        agents: Dict of agent ID -> Agent instance

    Returns:
        List of unique MCP server instances
    """
    tools: list[Any] = []
    seen: set[int] = set()

    for agent_id, agent in agents.items():
        if hasattr(agent, "tools") and agent.tools:
            for tool in agent.tools:
                if _is_mcp_server(tool):
                    tool_id = id(tool)
                    if tool_id not in seen:
                        seen.add(tool_id)
                        tools.append(tool)
                        tool_name = getattr(tool, "name", "unnamed")
                        logger.info(f"Discovered MCP tool '{tool_name}' in agent: {agent_id}")

    if tools:
        logger.info(f"Total MCP tools: {len(tools)}")

    return tools


def discover_rag_pipelines(agents: dict[str, Any]) -> list[Any]:
    """
    Discover RAG pipelines from agents.

    Args:
        agents: Dict of agent ID -> Agent instance

    Returns:
        List of unique RAG pipeline instances
    """
    pipelines: list[Any] = []
    seen: set[int] = set()

    for agent_id, agent in agents.items():
        if hasattr(agent, "rag_pipeline") and agent.rag_pipeline is not None:
            pipeline_id = id(agent.rag_pipeline)
            if pipeline_id not in seen:
                seen.add(pipeline_id)
                pipelines.append(agent.rag_pipeline)
                logger.info(f"Discovered RAG pipeline in agent: {agent_id}")

    if pipelines:
        logger.info(f"Total RAG pipelines: {len(pipelines)}")

    return pipelines


def _is_mcp_server(tool: Any) -> bool:
    """
    Check if a tool is an MCP server.

    Uses duck typing to avoid import issues.
    """
    # Check by class name (duck typing)
    class_name = type(tool).__name__
    if class_name in ("MCPServer", "MCPManager"):
        return True

    # Check for MCP-specific methods
    if hasattr(tool, "connect") and hasattr(tool, "close"):
        # Could be MCP - check for tool listing
        if hasattr(tool, "list_tools") or hasattr(tool, "get_tools"):
            return True

    return False


def create_registry(
    agents: dict[str, Any],
    teams: dict[str, Any] | None = None,
    global_storage: Any | None = None,
) -> AgentRegistry:
    """
    Create and populate an AgentRegistry.

    This is the main entry point for registry creation.
    Validates inputs and discovers all resources.

    Args:
        agents: Dict of agent ID -> Agent instance
        teams: Optional dict of team ID -> Team instance
        global_storage: Optional global storage fallback

    Returns:
        Populated AgentRegistry

    Raises:
        ValueError: If validation fails (fail loud)
    """
    # Validate (fail loud)
    validate_agents(agents)

    # Discover resources
    discovered = discover_all(agents, global_storage)

    # Create registry
    registry = AgentRegistry(
        agents=agents,
        teams=teams or {},
        storage=discovered["storage"],
        mcp_tools=discovered["mcp_tools"],
        rag_pipelines=discovered["rag_pipelines"],
    )

    logger.info(
        f"Registry created: "
        f"{len(registry.agents)} agents, "
        f"{len(registry.teams)} teams, "
        f"{len(registry.storage)} storage backends, "
        f"{len(registry.mcp_tools)} MCP tools, "
        f"{len(registry.rag_pipelines)} RAG pipelines"
    )

    return registry
