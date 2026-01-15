"""
Integration tests for Stream Advanced.

Test Cases:
1. test_stream_multiple_sequential - Multiple sequential streams work correctly with content.
2. test_stream_response_content - Streaming produces coherent content about the topic.
3. test_stream_with_max_tokens - max_tokens override works in streaming.
4. test_stream_with_temperature - Temperature override works in streaming and produces output.
5. test_stream_with_tool - Streaming works when agent has tools and produces content.
"""

from framework.agents import Agent
from framework.agents.tool import tool
import pytest


@pytest.mark.integration
class TestStreamAdvanced:
    """Advanced streaming tests with content verification."""

    @pytest.mark.asyncio
    async def test_stream_with_tool(self, hf_model):
        """Streaming works when agent has tools and produces content."""

        @tool
        def get_info() -> str:
            """Get important information."""
            return "The answer is 42"

        agent = Agent(
            name="StreamToolAgent",
            instructions="Use tools when asked for info. Include the result in your response.",
            model=hf_model,
            tools=[get_info],
        )

        full_response = ""
        chunk_count = 0
        async for chunk in agent.stream("Tell me the important information"):
            if isinstance(chunk, str):
                full_response += chunk
                chunk_count += 1

        # Cross-verify: Got chunks and content
        assert chunk_count > 0, "Should have received streaming chunks"
        assert len(full_response) > 0, "Streamed content should not be empty"

    @pytest.mark.asyncio
    async def test_stream_response_content(self, hf_model):
        """Streaming produces coherent content about the topic."""
        agent = Agent(
            name="ContentAgent",
            instructions="Be helpful and respond clearly.",
            model=hf_model,
        )

        full_response = ""
        async for chunk in agent.stream("Say hello and introduce yourself"):
            if isinstance(chunk, str):
                full_response += chunk

        # Cross-verify: Response has content and is about greeting
        assert len(full_response) > 0, "Streamed content should not be empty"
        response_lower = full_response.lower()
        assert (
            "hello" in response_lower
            or "hi" in response_lower
            or "greeting" in response_lower
            or "assistant" in response_lower
        ), f"Streamed response should be greeting-like. Got: {full_response}"

    @pytest.mark.asyncio
    async def test_stream_with_temperature(self, hf_model):
        """Temperature override works in streaming and produces output."""
        agent = Agent(
            name="TempAgent",
            instructions="Be helpful.",
            model=hf_model,
        )

        full_response = ""
        async for chunk in agent.stream("Count to 3", temperature=0.1):
            if isinstance(chunk, str):
                full_response += chunk

        # Cross-verify: Got content
        assert len(full_response) > 0, "Should have produced content"
        # Verify response contains numbers (counting)
        has_numbers = any(char.isdigit() for char in full_response)
        assert (
            has_numbers
            or "one" in full_response.lower()
            or "two" in full_response.lower()
            or "three" in full_response.lower()
        ), f"Streamed response should mention numbers. Got: {full_response}"

    @pytest.mark.asyncio
    async def test_stream_with_max_tokens(self, hf_model):
        """max_tokens override works in streaming."""
        agent = Agent(
            name="TokenAgent",
            instructions="Be helpful.",
            model=hf_model,
        )

        full_response = ""
        async for chunk in agent.stream("Tell me a story", max_tokens=30):
            if isinstance(chunk, str):
                full_response += chunk

        # Cross-verify: Got some content (limited by max_tokens)
        assert len(full_response) > 0, "Should have produced content"
        # Response should be shorter due to max_tokens limit
        assert len(full_response) < 500, (
            f"Response should be limited by max_tokens. Got length: {len(full_response)}"
        )

    @pytest.mark.asyncio
    async def test_stream_multiple_sequential(self, hf_model):
        """Multiple sequential streams work correctly with content."""
        agent = Agent(
            name="MultiStreamAgent",
            instructions="Be concise. Respond with single words when asked.",
            model=hf_model,
        )

        # First stream
        response1 = ""
        async for chunk in agent.stream("Say 'one'"):
            if isinstance(chunk, str):
                response1 += chunk

        # Second stream
        response2 = ""
        async for chunk in agent.stream("Say 'two'"):
            if isinstance(chunk, str):
                response2 += chunk

        assert len(response1) > 0, "First stream should produce content"
        assert len(response2) > 0, "Second stream should produce content"
        # Verify responses are different (different requests)
        assert response1 != response2, "Responses should be different for different inputs"
        # Verify responses contain expected content
        response1_lower = response1.lower()
        response2_lower = response2.lower()
        assert "one" in response1_lower or "1" in response1, (
            f"First response should mention 'one'. Got: {response1}"
        )
        assert "two" in response2_lower or "2" in response2, (
            f"Second response should mention 'two'. Got: {response2}"
        )
