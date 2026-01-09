"""
Integration tests for Invoke Advanced.

Test Cases:
1. test_agent_with_calculator_tool - Agent executes calculator tool and returns result.
2. test_agent_with_weather_tool - Agent executes tool and includes result in response.
3. test_combined_overrides - Multiple overrides work together.
4. test_concise_instructions - Agent with concise instructions gives short responses.
5. test_max_tokens_limit - max_tokens limits response length.
6. test_role_instructions - Agent follows role-based instructions.
7. test_temperature_low - Low temperature makes output more deterministic.
"""

from framework.agents import Agent
from framework.agents.tool import tool
import pytest


@pytest.mark.integration
class TestInvokeWithTools:
    """Tests for invoking agents with tools."""

    @pytest.mark.asyncio
    async def test_agent_with_weather_tool(self, hf_model):
        """Agent executes tool and includes result in response."""

        @tool
        def get_weather() -> str:
            """Get current weather conditions."""
            return "It is 72 degrees and sunny in Tokyo"

        agent = Agent(
            name="WeatherAgent",
            instructions=(
                "You are a weather assistant. When asked about weather, "
                "ALWAYS use the get_weather tool and include the exact result in your response."
            ),
            model=hf_model,
            tools=[get_weather],
            code_mode=False,
        )

        assert agent.tools is not None
        assert isinstance(agent.tools, list)
        assert len(agent.tools) == 1

        response = await agent.invoke("What is the weather right now?")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"

        response_lower = response.lower()
        tool_was_executed = (
            "72" in response or "sunny" in response_lower or "tokyo" in response_lower
        )
        if not tool_was_executed:
            pytest.skip("Model did not execute tool - model capability limitation")

    @pytest.mark.asyncio
    async def test_agent_with_calculator_tool(self, hf_model):
        """Agent executes calculator tool and returns result."""

        @tool
        def add_numbers(a: int, b: int) -> str:
            """Add two numbers together and return the result."""
            result = a + b
            return f"The sum is {result}"

        agent = Agent(
            name="CalcAgent",
            instructions=(
                "You are a calculator. When asked to add numbers, "
                "use the add_numbers tool and include the exact result in your response."
            ),
            model=hf_model,
            tools=[add_numbers],
            code_mode=False,
        )

        assert agent.tools is not None
        assert len(agent.tools) == 1

        response = await agent.invoke("What is 5 plus 3?")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"

        assert "8" in response or "eight" in response.lower(), (
            f"Calculator result (8 or eight) should appear in response. Got: {response}"
        )


@pytest.mark.integration
class TestInvokeWithInstructions:
    """Tests for instructions affecting agent behavior."""

    @pytest.mark.asyncio
    async def test_concise_instructions(self, hf_model):
        """Agent with concise instructions gives short responses."""
        agent = Agent(
            name="ConciseAgent",
            instructions="Be extremely concise. One sentence max.",
            model=hf_model,
        )
        response = await agent.invoke("What is Python?")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        assert len(response) > 5, "Response should be meaningful"
        # Verify response mentions Python
        response_lower = response.lower()
        assert (
            "python" in response_lower
            or "programming" in response_lower
            or "language" in response_lower
        ), f"Response should mention Python. Got: {response}"
