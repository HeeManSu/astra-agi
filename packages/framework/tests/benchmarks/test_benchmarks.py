"""
Benchmark tests for Astra Framework.

Performance targets:
- Agent instantiation: <5μs (target: 3-4μs)
- Memory footprint: <10KB per agent
- Batch 1000 agents: <5ms total
- Agent with 10 tools: <10μs

Run with:
    pytest tests/benchmarks/ -v --benchmark-only
    pytest tests/benchmarks/ --benchmark-only --benchmark-verbose
"""

import sys

from framework.agents.agent import Agent
from framework.agents.tool import tool
from framework.models.google.gemini import Gemini
import pytest


@pytest.mark.benchmark
def test_agent_instantiation_time(benchmark):
    """
    Benchmark: Agent instantiation time.
    Target: <5μs (ideally 3-4μs)
    """

    def create_agent():
        return Agent(
            name="BenchAgent",
            instructions="You are a helpful assistant",
            model=Gemini("gemini-1.5-flash"),
        )

    result = benchmark(create_agent)

    # Verify agent was created
    assert result is not None
    assert result.name == "BenchAgent"


@pytest.mark.benchmark
def test_agent_instantiation_with_all_params(benchmark):
    """
    Benchmark: Agent with all parameters.
    Target: <10μs
    """

    def create_full_agent():
        return Agent(
            name="FullAgent",
            id="custom-id-123",
            description="A fully configured agent",
            instructions="You are helpful",
            model=Gemini("gemini-1.5-flash"),
            tools=None,
            max_retries=5,
            temperature=0.8,
            max_tokens=2048,
            stream=True,
        )

    result = benchmark(create_full_agent)
    assert result.name == "FullAgent"
    assert result.id == "custom-id-123"


@pytest.mark.benchmark
def test_agent_memory_footprint(benchmark):
    """
    Benchmark: Agent memory footprint.
    Target: <10KB per agent
    """

    def measure_agent_size():
        agent = Agent(
            name="MemAgent",
            instructions="Test",
            model=Gemini("gemini-1.5-flash"),
        )
        # Get size of agent object
        return sys.getsizeof(agent)

    size_bytes = benchmark(measure_agent_size)

    # Assert target
    assert size_bytes < 10 * 1024, f"Agent too large: {size_bytes / 1024:.2f} KB"


@pytest.mark.benchmark
def test_batch_agent_creation_1000(benchmark):
    """
    Benchmark: Create 1000 agents.
    Target: <5ms total (5μs per agent)
    """

    def create_1000_agents():
        return [
            Agent(
                name=f"Agent{i}",
                instructions="Test",
                model=Gemini("gemini-1.5-flash"),
            )
            for i in range(1000)
        ]

    agents = benchmark(create_1000_agents)

    assert len(agents) == 1000
    assert all(isinstance(a, Agent) for a in agents)


@pytest.mark.benchmark
def test_agent_with_tools_instantiation(benchmark):
    """
    Benchmark: Agent with 10 tools.
    Target: <10μs
    """

    # Create 10 sample tools
    @tool
    def tool_1(x: int) -> int:
        """Tool 1"""
        return x * 2

    @tool
    def tool_2(x: int) -> int:
        """Tool 2"""
        return x * 3

    @tool
    def tool_3(x: int) -> int:
        """Tool 3"""
        return x * 4

    @tool
    def tool_4(x: int) -> int:
        """Tool 4"""
        return x * 5

    @tool
    def tool_5(x: int) -> int:
        """Tool 5"""
        return x * 6

    @tool
    def tool_6(x: int) -> int:
        """Tool 6"""
        return x * 7

    @tool
    def tool_7(x: int) -> int:
        """Tool 7"""
        return x * 8

    @tool
    def tool_8(x: int) -> int:
        """Tool 8"""
        return x * 9

    @tool
    def tool_9(x: int) -> int:
        """Tool 9"""
        return x * 10

    @tool
    def tool_10(x: int) -> int:
        """Tool 10"""
        return x * 11

    tools = [tool_1, tool_2, tool_3, tool_4, tool_5, tool_6, tool_7, tool_8, tool_9, tool_10]

    def create_agent_with_tools():
        return Agent(
            name="ToolAgent",
            instructions="Test",
            model=Gemini("gemini-1.5-flash"),
            tools=tools,
        )

    result = benchmark(create_agent_with_tools)
    assert result.tools == tools
    assert len(result.tools) == 10


@pytest.mark.benchmark
def test_tool_creation_benchmark(benchmark):
    """
    Benchmark: Tool creation time.
    Target: <1μs per tool
    """

    def create_tool():
        @tool
        def sample_tool(a: int, b: str, c: list[int]) -> dict:
            """A sample tool."""
            return {"a": a, "b": b, "c": c}

        return sample_tool

    result = benchmark(create_tool)
    assert result.name == "sample_tool"


@pytest.mark.benchmark
def test_lazy_tools_schema_access(benchmark):
    """
    Benchmark: Accessing tools_schema property (lazy computation).
    This should be fast on first access and cached thereafter.
    """

    @tool
    def sample_tool(x: int, y: str) -> str:
        """Sample tool"""
        return f"{x}{y}"

    agent = Agent(
        name="SchemaAgent",
        instructions="Test",
        model=Gemini("gemini-1.5-flash"),
        tools=[sample_tool],
    )

    def access_tools_schema():
        return agent.tools_schema

    schema = benchmark(access_tools_schema)

    assert len(schema) == 1
    assert schema[0]["name"] == "sample_tool"


@pytest.mark.benchmark
def test_lazy_context_access(benchmark):
    """
    Benchmark: Accessing context property (lazy initialization).
    """

    agent = Agent(
        name="ContextAgent",
        instructions="Test",
        model=Gemini("gemini-1.5-flash"),
    )

    def access_context():
        return agent.context

    context = benchmark(access_context)
    assert context is not None


@pytest.mark.benchmark
def test_model_instantiation(benchmark):
    """
    Benchmark: Gemini model instantiation.
    Target: <5μs
    """

    def create_model():
        return Gemini("gemini-1.5-flash")

    model = benchmark(create_model)
    assert model.model_id == "gemini-1.5-flash"
    assert model.provider == "gemini"


@pytest.mark.benchmark
def test_agent_repr(benchmark):
    """
    Benchmark: Agent __repr__ performance.
    Should be very fast with minimal representation.
    """

    agent = Agent(
        name="ReprAgent",
        instructions="Test",
        model=Gemini("gemini-1.5-flash"),
    )

    def get_repr():
        return repr(agent)

    result = benchmark(get_repr)
    assert "ReprAgent" in result
    assert "agent-" in result  # ID prefix
