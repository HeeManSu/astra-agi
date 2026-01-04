"""
Tests for Astra Server Registry.

Tests AgentRegistry, validation functions, and discovery functions.
"""

from astra.server.registry import (
    AgentRegistry,
    StorageInfo,
    create_registry,
    discover_mcp_tools,
    discover_rag_pipelines,
    discover_storage,
    validate_agents,
)
import pytest

from .conftest import (  # noqa: TID252
    SimpleMCPServer,
    create_agent,
    create_rag_pipeline,
    create_storage,
)


# ============================================================================
# AgentRegistry Class Tests
# ============================================================================


class TestAgentRegistryBasic:
    """Test AgentRegistry basic operations."""

    def test_empty_registry(self):
        """Empty registry has no agents."""
        registry = AgentRegistry()
        assert len(registry.agents) == 0

    def test_get_agent_unknown(self):
        """get_agent returns None for unknown name."""
        registry = AgentRegistry()
        assert registry.get_agent("unknown") is None

    def test_get_agent_known(self):
        """get_agent returns agent for known name."""
        agent = create_agent(name="test")
        registry = AgentRegistry(agents={"test": agent})
        assert registry.get_agent("test") is agent

    def test_list_agent_names_empty(self):
        """list_agent_names returns empty list when empty."""
        registry = AgentRegistry()
        assert registry.list_agent_names() == []

    def test_list_agent_names_multiple(self):
        """list_agent_names returns all names."""
        registry = AgentRegistry(
            agents={
                "agent1": create_agent(name="agent1"),
                "agent2": create_agent(name="agent2"),
            }
        )
        names = registry.list_agent_names()
        assert sorted(names) == ["agent1", "agent2"]


class TestAgentRegistryStorage:
    """Test AgentRegistry storage operations."""

    def test_get_storage_no_storage(self):
        """get_storage_for_agent returns None when no storage."""
        registry = AgentRegistry()
        assert registry.get_storage_for_agent("test") is None

    def test_get_storage_with_storage(self):
        """get_storage_for_agent returns storage when exists."""
        storage = create_storage()
        storage_info = StorageInfo(
            id="storage-0",
            instance=storage,
            type_name="MockStorage",
            used_by=["test"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})
        assert registry.get_storage_for_agent("test") is storage

    def test_get_storage_wrong_agent(self):
        """get_storage_for_agent returns None for different agent."""
        storage = create_storage()
        storage_info = StorageInfo(
            id="storage-0",
            instance=storage,
            type_name="MockStorage",
            used_by=["other"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})
        assert registry.get_storage_for_agent("test") is None


# ============================================================================
# Validation Tests (Fail Loud)
# ============================================================================


class TestValidateAgents:
    """Test validate_agents fail-loud behavior."""

    def test_empty_dict_raises(self):
        """Empty dict raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_agents({})
        assert "No agents registered" in str(exc_info.value)
        assert "create_app(agents=" in str(exc_info.value)

    def test_none_agent_raises(self):
        """None agent value raises ValueError with name."""
        with pytest.raises(ValueError) as exc_info:
            validate_agents({"my-agent": None})
        assert "my-agent" in str(exc_info.value)
        assert "None" in str(exc_info.value)

    def test_agent_without_invoke_raises(self):
        """Agent without invoke method raises ValueError."""

        class InvalidAgent:
            pass

        with pytest.raises(ValueError) as exc_info:
            validate_agents({"bad-agent": InvalidAgent()})
        assert "bad-agent" in str(exc_info.value)
        assert "invoke" in str(exc_info.value)

    def test_valid_single_agent_passes(self):
        """Valid single agent passes validation."""
        agent = create_agent()
        validate_agents({"test": agent})  # Should not raise

    def test_valid_multiple_agents_pass(self):
        """Valid multiple agents pass validation."""
        agents = {
            "agent1": create_agent(name="agent1"),
            "agent2": create_agent(name="agent2"),
        }
        validate_agents(agents)  # Should not raise

    def test_error_includes_type_name(self):
        """Error message includes actual type name."""

        class NotAnAgent:
            pass

        with pytest.raises(ValueError) as exc_info:
            validate_agents({"test": NotAnAgent()})
        assert "NotAnAgent" in str(exc_info.value)


# ============================================================================
# Storage Discovery Tests
# ============================================================================


class TestDiscoverStorage:
    """Test discover_storage function."""

    def test_agent_without_storage_attribute(self):
        """Agent without storage attribute is skipped."""

        class NoStorageAgent:
            async def invoke(self, message):
                return message

        result = discover_storage({"test": NoStorageAgent()})
        assert len(result) == 0

    def test_agent_with_none_storage(self):
        """Agent with storage=None is skipped."""
        agent = create_agent(storage=None)
        result = discover_storage({"test": agent})
        assert len(result) == 0

    def test_agent_with_storage(self):
        """Agent with storage is discovered."""
        storage = create_storage()
        agent = create_agent(storage=storage)
        result = discover_storage({"test": agent})
        # Should discover exactly one storage
        assert len(result) == 1

    def test_shared_storage_deduplicated(self):
        """Multiple agents with same storage are deduplicated."""
        storage = create_storage()
        # Use same storage instance in both agents
        agent1 = create_agent(name="agent1", storage=storage)
        agent2 = create_agent(name="agent2", storage=storage)
        # Force same storage on agent2 since create_agent may wrap it
        agent2.storage = agent1.storage
        result = discover_storage({"agent1": agent1, "agent2": agent2})
        assert len(result) == 1

    def test_different_storage_all_discovered(self):
        """Multiple agents with different storage are all discovered."""
        storage1 = create_storage("storage1")
        storage2 = create_storage("storage2")
        agent1 = create_agent(name="agent1", storage=storage1)
        agent2 = create_agent(name="agent2", storage=storage2)
        result = discover_storage({"agent1": agent1, "agent2": agent2})
        assert len(result) == 2

    def test_global_storage_applied(self):
        """Global storage is applied to agents without storage."""
        global_storage = create_storage("global")
        agent = create_agent(storage=None)
        result = discover_storage({"test": agent}, global_storage=global_storage)
        assert len(result) == 1
        assert agent.storage is global_storage

    def test_global_storage_no_override(self):
        """Global storage doesn't override existing agent storage."""
        global_storage = create_storage("global")
        agent_storage = create_storage("agent")
        agent = create_agent(storage=agent_storage)
        original_storage = agent.storage  # Capture before discover
        result = discover_storage({"test": agent}, global_storage=global_storage)
        assert len(result) == 1
        # Agent's storage should not be replaced by global
        assert agent.storage is original_storage

    def test_storage_info_used_by(self):
        """StorageInfo.used_by tracks all agent names."""
        storage = create_storage()
        agent1 = create_agent(name="agent1", storage=storage)
        agent2 = create_agent(name="agent2", storage=storage)
        # Force same storage on agent2 since create_agent may wrap it
        agent2.storage = agent1.storage
        result = discover_storage({"agent1": agent1, "agent2": agent2})
        storage_info = next(iter(result.values()))
        assert "agent1" in storage_info.used_by
        assert "agent2" in storage_info.used_by

    def test_storage_info_id_unique(self):
        """StorageInfo.id is unique for each storage."""
        storage1 = create_storage("s1")
        storage2 = create_storage("s2")
        agent1 = create_agent(storage=storage1)
        agent2 = create_agent(storage=storage2)
        result = discover_storage({"a1": agent1, "a2": agent2})
        ids = [info.id for info in result.values()]
        assert len(ids) == len(set(ids))  # All unique

    def test_storage_info_type_name(self):
        """StorageInfo.type_name is correct class name."""
        storage = create_storage()
        agent = create_agent(storage=storage)
        result = discover_storage({"test": agent})
        storage_info = next(iter(result.values()))
        # Should be AgentStorage since that's what create_storage returns
        assert storage_info.type_name == "AgentStorage"


# ============================================================================
# MCP Discovery Tests
# ============================================================================


class TestDiscoverMCPTools:
    """Test discover_mcp_tools function."""

    def test_agent_without_tools(self):
        """Agent without tools attribute is skipped."""

        class NoToolsAgent:
            async def invoke(self, message):
                return message

        result = discover_mcp_tools({"test": NoToolsAgent()})
        assert len(result) == 0

    def test_agent_with_empty_tools(self):
        """Agent with empty tools list is skipped."""
        agent = create_agent(tools=[])
        result = discover_mcp_tools({"test": agent})
        assert len(result) == 0

    def test_regular_tool_ignored(self):
        """Regular non-MCP tools are ignored."""

        class RegularTool:
            pass

        agent = create_agent(tools=[RegularTool()])
        result = discover_mcp_tools({"test": agent})
        assert len(result) == 0

    def test_mcp_server_detected(self):
        """MCPServer class is detected."""
        mcp = SimpleMCPServer()
        agent = create_agent(tools=[mcp])
        result = discover_mcp_tools({"test": agent})
        assert len(result) == 1
        assert mcp in result

    def test_mcp_deduplicated(self):
        """Multiple agents with same MCP are deduplicated."""
        mcp = SimpleMCPServer()
        agent1 = create_agent(tools=[mcp])
        agent2 = create_agent(tools=[mcp])
        result = discover_mcp_tools({"a1": agent1, "a2": agent2})
        assert len(result) == 1

    def test_multiple_mcp_discovered(self):
        """Multiple different MCPs are all discovered."""
        mcp1 = SimpleMCPServer("mcp1")
        mcp2 = SimpleMCPServer("mcp2")
        agent = create_agent(tools=[mcp1, mcp2])
        result = discover_mcp_tools({"test": agent})
        assert len(result) == 2


# ============================================================================
# RAG Discovery Tests
# ============================================================================


class TestDiscoverRagPipelines:
    """Test discover_rag_pipelines function."""

    def test_agent_without_rag(self):
        """Agent without rag_pipeline attribute is skipped."""

        class NoRagAgent:
            async def invoke(self, message):
                return message

        result = discover_rag_pipelines({"test": NoRagAgent()})
        assert len(result) == 0

    def test_agent_with_none_rag(self):
        """Agent with rag_pipeline=None is skipped."""
        agent = create_agent(rag_pipeline=None)
        result = discover_rag_pipelines({"test": agent})
        assert len(result) == 0

    def test_agent_with_rag(self):
        """Agent with RAG is discovered."""
        rag = create_rag_pipeline()
        agent = create_agent(rag_pipeline=rag)
        result = discover_rag_pipelines({"test": agent})
        assert len(result) == 1
        assert rag in result

    def test_shared_rag_deduplicated(self):
        """Multiple agents with same RAG are deduplicated."""
        rag = create_rag_pipeline()
        agent1 = create_agent(rag_pipeline=rag)
        agent2 = create_agent(rag_pipeline=rag)
        result = discover_rag_pipelines({"a1": agent1, "a2": agent2})
        assert len(result) == 1

    def test_multiple_rag_discovered(self):
        """Multiple different RAGs are all discovered."""
        rag1 = create_rag_pipeline("rag1")
        rag2 = create_rag_pipeline("rag2")
        agent1 = create_agent(rag_pipeline=rag1)
        agent2 = create_agent(rag_pipeline=rag2)
        result = discover_rag_pipelines({"a1": agent1, "a2": agent2})
        assert len(result) == 2


# ============================================================================
# create_registry Integration Tests
# ============================================================================


class TestCreateRegistry:
    """Test create_registry integration."""

    def test_single_agent(self):
        """Single agent creates valid registry."""
        agent = create_agent()
        registry = create_registry(agents={"test": agent})
        assert len(registry.agents) == 1
        assert registry.get_agent("test") is agent

    def test_multiple_agents(self):
        """Multiple agents create valid registry."""
        registry = create_registry(
            agents={
                "a1": create_agent(name="a1"),
                "a2": create_agent(name="a2"),
            }
        )
        assert len(registry.agents) == 2

    def test_with_global_storage(self):
        """Global storage is passed through."""
        storage = create_storage()
        agent = create_agent()
        _registry = create_registry(agents={"test": agent}, global_storage=storage)
        assert agent.storage is storage

    def test_validation_errors_propagate(self):
        """Validation errors propagate."""
        with pytest.raises(ValueError):
            create_registry(agents={})

    def test_all_discoveries_combined(self):
        """All discoveries are combined into registry."""
        storage = create_storage()
        mcp = SimpleMCPServer()
        rag = create_rag_pipeline()
        agent = create_agent(storage=storage, tools=[mcp], rag_pipeline=rag)

        registry = create_registry(agents={"test": agent})

        assert len(registry.storage) == 1
        assert len(registry.mcp_tools) == 1
        assert len(registry.rag_pipelines) == 1
