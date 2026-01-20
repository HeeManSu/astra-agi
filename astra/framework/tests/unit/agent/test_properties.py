"""
Unit tests for Agent properties and initialization.

These tests verify agent properties, initialization, and configuration
without making any LLM calls. All tests are fast and have no external dependencies.

Test Cases:
1. test_agent_id_auto_generated - Agent ID is auto-generated if not provided
2. test_agent_id_custom - Custom agent ID is preserved
3. test_agent_name_preserved - Agent name is set correctly
4. test_agent_instructions_preserved - Agent instructions are set correctly
5. test_agent_description - Agent description is optional and preserved
6. test_agent_default_values - Agent has sensible defaults
7. test_tools_schema_empty_when_no_tools - tools_schema is empty when agent has no tools
8. test_tools_schema_populated_with_tools - tools_schema is populated when agent has tools
9. test_tools_schema_multiple_tools - tools_schema works with multiple tools
10. test_context_not_initialized_at_creation - Context is not initialized at agent creation
11. test_context_initialized_on_access - Context is initialized when accessed
12. test_stream_enabled_default_false - stream_enabled defaults to False
13. test_stream_enabled_true - stream_enabled can be set to True
14. test_default_memory_config - Default Memory is applied
15. test_custom_memory_config - Custom Memory is preserved
"""

from framework.agents import Agent
from framework.agents.tool import tool
from framework.memory import Memory
from framework.models.huggingface import HuggingFaceLocal
import pytest


@pytest.fixture
def mock_model():
    """Mock model for unit tests (not actually used)."""
    return HuggingFaceLocal("HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=10)


@pytest.mark.unit
class TestAgentInit:
    """Tests for Agent __init__ and basic properties."""

    def test_agent_id_auto_generated(self, mock_model):
        """Agent ID is auto-generated if not provided."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )
        assert agent.id is not None
        assert agent.id.startswith("agent-")
        assert len(agent.id) > 10

    def test_agent_id_custom(self, mock_model):
        """Custom agent ID is preserved."""
        custom_id = "my-custom-agent-123"
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
            id=custom_id,
        )
        assert agent.id == custom_id

    def test_agent_name_preserved(self, mock_model):
        """Agent name is set correctly."""
        agent = Agent(
            name="MySpecialAgent",
            instructions="You are helpful.",
            model=mock_model,
        )
        assert agent.name == "MySpecialAgent"

    def test_agent_instructions_preserved(self, mock_model):
        """Agent instructions are set correctly."""
        instructions = "You are a math expert. Always show your work."
        agent = Agent(
            name="MathAgent",
            instructions=instructions,
            model=mock_model,
        )
        assert agent.instructions == instructions

    def test_agent_description(self, mock_model):
        """Agent description is optional and preserved."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
            description="A test agent for unit tests.",
        )
        assert agent.description == "A test agent for unit tests."

    def test_agent_default_values(self, mock_model):
        """Agent has sensible defaults."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )
        assert agent.max_retries == 3
        assert agent.temperature == 0.7
        assert agent.stream_enabled is False
        assert agent.code_mode is True


@pytest.mark.unit
class TestToolsSchema:
    """Tests for tools_schema property."""

    def test_tools_schema_empty_when_no_tools(self, mock_model):
        """tools_schema is empty when agent has no tools."""
        agent = Agent(
            name="NoToolsAgent",
            instructions="You are helpful.",
            model=mock_model,
            tools=None,
        )
        assert agent.tools_schema == []

    def test_tools_schema_populated_with_tools(self, mock_model):
        """tools_schema is populated when agent has tools."""

        @tool
        def calculator(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        agent = Agent(
            name="CalcAgent",
            instructions="You are helpful.",
            model=mock_model,
            tools=[calculator],
        )

        schema = agent.tools_schema
        assert len(schema) == 1
        assert schema[0]["name"] == "calculator"
        assert "description" in schema[0]
        assert "parameters" in schema[0]

    def test_tools_schema_multiple_tools(self, mock_model):
        """tools_schema works with multiple tools."""

        @tool
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        @tool
        def multiply(a: int, b: int) -> int:
            """Multiply two numbers."""
            return a * b

        agent = Agent(
            name="MathAgent",
            instructions="You are helpful.",
            model=mock_model,
            tools=[add, multiply],
        )

        schema = agent.tools_schema
        assert len(schema) == 2
        tool_names = [s["name"] for s in schema]
        assert "add" in tool_names
        assert "multiply" in tool_names


@pytest.mark.unit
class TestContextLazyInit:
    """Tests for lazy context initialization."""

    def test_context_not_initialized_at_creation(self, mock_model):
        """Context is not initialized at agent creation."""
        agent = Agent(
            name="LazyAgent",
            instructions="You are helpful.",
            model=mock_model,
        )
        # Access the private attribute directly
        assert agent._context is None

    def test_context_initialized_on_access(self, mock_model):
        """Context is initialized when accessed."""
        agent = Agent(
            name="LazyAgent",
            instructions="You are helpful.",
            model=mock_model,
        )
        # Access the property (this triggers initialization)
        context = agent.context
        assert context is not None
        assert agent._context is not None


@pytest.mark.unit
class TestStreamEnabledProperty:
    """Tests for stream_enabled property."""

    def test_stream_enabled_default_false(self, mock_model):
        """stream_enabled defaults to False."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )
        assert agent.stream_enabled is False

    def test_stream_enabled_true(self, mock_model):
        """stream_enabled can be set to True."""
        agent = Agent(
            name="StreamAgent",
            instructions="You are helpful.",
            model=mock_model,
            stream_enabled=True,
        )
        assert agent.stream_enabled is True


@pytest.mark.unit
class TestMemoryConfiguration:
    """Tests for memory configuration."""

    def test_default_memory_config(self, mock_model):
        """Default Memory is applied."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
        )
        assert agent.memory is not None
        assert isinstance(agent.memory, Memory)

    def test_custom_memory_config(self, mock_model):
        """Custom Memory is preserved."""
        custom_memory = Memory(
            num_history_turns=10,
            add_history_to_messages=True,
        )
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=mock_model,
            memory=custom_memory,
        )
        assert agent.memory.num_history_turns == 10
        assert agent.memory.add_history_to_messages is True
