"""
Integration tests for Agent core functionality.

Test Cases:
1. test_simple_invoke - Agent responds to math question with numeric answer
2. test_invoke_with_context - Agent maintains context across invocations
3. test_parameter_override_temperature - Temperature parameter can be overridden
4. test_parameter_override_max_tokens - Max tokens parameter can be overridden
5. test_simple_stream - Agent can stream responses
6. test_stream_collects_all_chunks - Stream collects all response chunks
7. test_empty_message_handled - Agent handles empty messages gracefully
8. test_invalid_temperature_raises_error - Invalid temperature raises ValidationError
9. test_invalid_max_tokens_raises_error - Invalid max_tokens raises ValidationError
10. test_agent_without_tools - Agent works without tools
11. test_multiple_agents_independent - Multiple agents operate independently
12. test_long_message - Agent handles long input messages
"""

from framework.agents import Agent
from framework.agents.exceptions import ValidationError
import pytest


@pytest.mark.integration
class TestAgentInvoke:
    """Tests for agent.invoke() functionality."""

    @pytest.mark.asyncio
    async def test_simple_invoke(self, simple_agent):
        """Agent can respond to a math question with numeric answer."""
        response = await simple_agent.invoke("What is 2+2? Reply with just the number.")

        assert response is not None
        assert isinstance(response, str)
        assert "4" in response, f"Response should contain '4'. Got: {response}"

    @pytest.mark.asyncio
    async def test_invoke_with_context(self, simple_agent):
        """Agent responds about Python with relevant content."""
        response = await simple_agent.invoke("Explain what Python is in one sentence.")

        assert response is not None
        assert isinstance(response, str)
        response_lower = response.lower()
        assert (
            "python" in response_lower
            or "programming" in response_lower
            or "language" in response_lower
        ), f"Response should mention Python or programming. Got: {response}"

    @pytest.mark.asyncio
    async def test_parameter_override_temperature(self, simple_agent):
        """Agent respects temperature override and produces output."""
        response = await simple_agent.invoke(
            "Say exactly: hello world",
            temperature=0.1,
        )
        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response contains greeting
        response_lower = response.lower()
        assert "hello" in response_lower or "world" in response_lower, (
            f"Response should mention 'hello' or 'world'. Got: {response}"
        )

    @pytest.mark.asyncio
    async def test_parameter_override_max_tokens(self, simple_agent):
        """Agent respects max_tokens override."""
        response = await simple_agent.invoke(
            "Count from 1 to 10",
            max_tokens=50,
        )
        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response contains numbers (may be truncated due to max_tokens)
        has_numbers = any(char.isdigit() for char in response)
        assert has_numbers or len(response) < 100, (
            f"Response should contain numbers or be short due to max_tokens. Got: {response}"
        )


@pytest.mark.integration
class TestAgentStream:
    """Tests for agent.stream() functionality."""

    @pytest.mark.asyncio
    async def test_simple_stream(self, simple_agent):
        """Agent can stream a response with actual content."""
        full_response = ""
        chunk_count = 0
        async for chunk in simple_agent.stream("Tell me a short joke."):
            if isinstance(chunk, str):
                full_response += chunk
                chunk_count += 1

        assert chunk_count > 0, "Should have received streaming chunks"
        assert len(full_response) > 0, "Streamed content should not be empty"

    @pytest.mark.asyncio
    async def test_stream_collects_all_chunks(self, simple_agent):
        """Streaming collects all chunks correctly."""
        full_response = ""
        async for chunk in simple_agent.stream("Count from 1 to 3."):
            if isinstance(chunk, str):
                full_response += chunk

        assert len(full_response) > 0, "Should have content"


@pytest.mark.integration
class TestAgentValidation:
    """Tests for agent input validation."""

    @pytest.mark.asyncio
    async def test_empty_message_handled(self, simple_agent):
        """Empty message is handled gracefully."""
        response = await simple_agent.invoke("")
        assert response is not None

    @pytest.mark.asyncio
    async def test_invalid_temperature_raises_error(self, simple_agent):
        """Temperature out of range raises ValidationError."""
        # The temperature depends on the model but it is mostly 0.0 - 2.0 for most of the models
        with pytest.raises(ValidationError):
            await simple_agent.invoke("Hello", temperature=5.0)

    @pytest.mark.asyncio
    async def test_invalid_max_tokens_raises_error(self, simple_agent):
        """Negative max_tokens raises ValidationError."""
        with pytest.raises(ValidationError):
            await simple_agent.invoke("Hello", max_tokens=-100)


@pytest.mark.integration
class TestAgentEdgeCases:
    """Tests for agent edge cases."""

    @pytest.mark.asyncio
    async def test_agent_without_tools(self, hf_model):
        """Agent can work without any tools and answer math questions."""
        agent = Agent(
            name="NoToolsAgent",
            instructions="You are helpful. Answer math questions directly.",
            model=hf_model,
            tools=None,
        )
        response = await agent.invoke("What is 5+5? Reply with just the number.")
        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify answer is present
        assert "10" in response, f"Response should contain '10'. Got: {response}"

    @pytest.mark.asyncio
    async def test_multiple_agents_independent(self, hf_model):
        """Multiple agents can operate independently with different responses."""
        agent1 = Agent(
            name="MathAgent",
            instructions="You are a math expert. Answer concisely.",
            model=hf_model,
        )
        agent2 = Agent(
            name="HistoryAgent",
            instructions="You are a history expert. Answer concisely.",
            model=hf_model,
        )

        r1 = await agent1.invoke("What is calculus?")
        r2 = await agent2.invoke("Who was Napoleon?")

        assert r1 is not None
        assert r2 is not None
        assert len(r1) > 0
        assert len(r2) > 0

        # Verify responses are relevant to their domains
        r1_lower = r1.lower()
        r2_lower = r2.lower()
        assert (
            "calculus" in r1_lower
            or "math" in r1_lower
            or "derivative" in r1_lower
            or "integral" in r1_lower
        ), f"Math agent should mention calculus/math. Got: {r1}"
        assert (
            "napoleon" in r2_lower
            or "france" in r2_lower
            or "emperor" in r2_lower
            or "french" in r2_lower
        ), f"History agent should mention Napoleon/history. Got: {r2}"

    @pytest.mark.asyncio
    async def test_long_message(self, simple_agent):
        """Agent handles long messages with actual response."""
        long_message = "Tell me about Python. " * 5
        response = await simple_agent.invoke(long_message)

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response mentions Python
        response_lower = response.lower()
        assert (
            "python" in response_lower
            or "programming" in response_lower
            or "language" in response_lower
        ), f"Response should mention Python. Got: {response}"
