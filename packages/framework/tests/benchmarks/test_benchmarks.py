import pytest
from framework.agents.agent import Agent
from framework.agents.tool import tool
from framework.astra import Astra

@pytest.mark.benchmark
def test_agent_initialization_benchmark(benchmark):
    """Benchmark agent initialization time."""
    def init_agent():
        return Agent(name="Bench", instructions="Test", model="google/gemini-1.5-flash")
    
    benchmark(init_agent)

@pytest.mark.benchmark
def test_tool_schema_generation_benchmark(benchmark):
    """Benchmark tool schema generation time."""
    def create_tool():
        @tool
        def complex_tool(a: int, b: str, c: list[int]) -> dict:
            """Complex tool."""
            return {}
        return complex_tool
    
    benchmark(create_tool)


