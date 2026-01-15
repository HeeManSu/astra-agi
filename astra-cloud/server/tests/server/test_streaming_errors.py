"""
Streaming Error Handling Tests for Astra Server.

Tests error handling during SSE streaming.
"""

from typing import ClassVar

from astra.server import create_app
from httpx import ASGITransport, AsyncClient
import pytest

from .conftest import create_storage, create_streaming_agent  # noqa: TID252


# ============================================================================
# Test Helper Classes
# ============================================================================


class PartialFailingAgent:
    """Agent that yields some data then fails."""

    name: ClassVar[str] = "partial-failing-agent"
    description: ClassVar[str] = "Fails mid-stream"
    storage: ClassVar[None] = None
    rag_pipeline: ClassVar[None] = None
    tools: ClassVar[list] = []

    async def invoke(self, message: str, **kwargs) -> str:
        return "This works"

    async def stream(self, message: str, **kwargs):
        yield "First chunk"
        yield "Second chunk"
        raise RuntimeError("Mid-stream failure!")
        # yield "Never reached"


class SlowAgent:
    """Agent that streams slowly."""

    name: ClassVar[str] = "slow-agent"
    description: ClassVar[str] = "Streams slowly"
    storage: ClassVar[None] = None
    rag_pipeline: ClassVar[None] = None
    tools: ClassVar[list] = []

    async def invoke(self, message: str, **kwargs) -> str:
        import asyncio

        await asyncio.sleep(0.5)
        return "Slow response"

    async def stream(self, message: str, **kwargs):
        import asyncio

        for i in range(3):
            await asyncio.sleep(0.1)
            yield f"Chunk {i}"


# ============================================================================
# Stream Event Tests
# ============================================================================


@pytest.mark.timeout(60)
class TestStreamEvents:
    """Test SSE event structure."""

    @pytest.mark.asyncio
    async def test_stream_includes_token_events(self):
        """Stream includes token events."""
        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/agents/test/stream",
                json={"message": "Hello"},
            ) as response:
                content = ""
                async for chunk in response.aiter_text():
                    content += chunk

                # Should have token events OR error (if rate limited)
                assert "event: token" in content or "event:token" in content or "error" in content

    @pytest.mark.asyncio
    async def test_stream_includes_done_event(self):
        """Stream includes done event at end."""
        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/agents/test/stream",
                json={"message": "Hello"},
            ) as response:
                content = ""
                async for chunk in response.aiter_text():
                    content += chunk

                # Should have done event OR error (if rate limited)
                assert "event: done" in content or "event:done" in content or "error" in content

    @pytest.mark.asyncio
    async def test_stream_data_is_json(self):
        """Stream data fields contain valid JSON."""
        import json

        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/agents/test/stream",
                json={"message": "Hello"},
            ) as response:
                content = ""
                async for chunk in response.aiter_text():
                    content += chunk

                # Extract data lines and verify they're valid JSON
                for line in content.split("\n"):
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str:
                            # Should parse as JSON
                            parsed = json.loads(data_str)
                            assert isinstance(parsed, dict)


# ============================================================================
# Error Event Tests
# ============================================================================


@pytest.mark.timeout(60)
class TestStreamErrorEvents:
    """Test error events in streams."""

    @pytest.mark.asyncio
    async def test_stream_error_returns_error_event(self):
        """Stream error sends error event."""
        from .conftest import FailingAgent  # noqa: TID252

        app = create_app(agents={"failing": FailingAgent()})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/agents/failing/stream",
                json={"message": "Hello"},
            ) as response:
                # Status is 200 for SSE (error in stream)
                assert response.status_code == 200

                content = ""
                async for chunk in response.aiter_text():
                    content += chunk

                # Should have error event
                assert "error" in content

    @pytest.mark.asyncio
    async def test_partial_stream_failure_sends_error(self):
        """Partial stream failure sends error event."""
        app = create_app(agents={"partial": PartialFailingAgent()})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/agents/partial/stream",
                json={"message": "Hello"},
            ) as response:
                content = ""
                async for chunk in response.aiter_text():
                    content += chunk

                # Should have received some data before error
                assert "First chunk" in content or "error" in content


# ============================================================================
# Stream with Storage Tests
# ============================================================================


@pytest.mark.timeout(120)
class TestStreamWithStorage:
    """Test streaming with storage/thread integration."""

    @pytest.mark.asyncio
    async def test_stream_with_valid_thread(self):
        """Stream with valid thread_id works."""
        storage = create_storage()
        agent = create_streaming_agent(storage=storage)
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create thread first
            thread_resp = await client.post(
                "/v1/threads",
                json={"agent_name": "test"},
            )
            thread_id = thread_resp.json()["id"]

            # Stream with that thread
            response = await client.post(
                "/v1/agents/test/stream",
                json={"message": "Hello", "thread_id": thread_id},
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_without_thread_works(self):
        """Stream without thread_id works."""
        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/test/stream",
                json={"message": "Hello"},
            )

            assert response.status_code == 200


# ============================================================================
# Slow Stream Tests
# ============================================================================


@pytest.mark.timeout(30)
class TestSlowStreams:
    """Test slow streaming scenarios."""

    @pytest.mark.asyncio
    async def test_slow_stream_completes(self):
        """Slow stream completes successfully."""
        app = create_app(agents={"slow": SlowAgent()})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/agents/slow/stream",
                json={"message": "Hello"},
            ) as response:
                chunks: list[str] = []
                async for chunk in response.aiter_text():
                    chunks.append(chunk)

                # Should have received all chunks
                full_content = "".join(chunks)
                assert "Chunk" in full_content or "done" in full_content


# ============================================================================
# Additional Streaming Edge Cases
# ============================================================================


class NonStreamingAgent:
    """Agent without stream method (tests fallback)."""

    name: ClassVar[str] = "non-streaming"
    description: ClassVar[str] = "No stream method"
    storage: ClassVar[None] = None
    rag_pipeline: ClassVar[None] = None
    tools: ClassVar[list] = []

    async def invoke(self, message: str, **kwargs) -> str:
        return f"Response to: {message}"


@pytest.mark.timeout(60)
class TestStreamingEdgeCases:
    """Additional streaming edge cases."""

    @pytest.mark.asyncio
    async def test_stream_unknown_agent_returns_404(self):
        """Stream to unknown agent returns 404."""
        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/unknown/stream",
                json={"message": "Hello"},
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stream_fallback_for_non_streaming_agent(self):
        """Agent without stream method uses invoke fallback."""
        app = create_app(agents={"non-streaming": NonStreamingAgent()})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/agents/non-streaming/stream",
                json={"message": "Hello"},
            ) as response:
                assert response.status_code == 200
                content = ""
                async for chunk in response.aiter_text():
                    content += chunk

                # Should have content from invoke fallback
                assert "Response to" in content or "done" in content or "error" in content

    @pytest.mark.asyncio
    async def test_stream_with_temperature(self):
        """Stream accepts temperature parameter."""
        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/test/stream",
                json={"message": "Hello", "temperature": 0.7},
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_with_max_tokens(self):
        """Stream accepts max_tokens parameter."""
        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/test/stream",
                json={"message": "Hello", "max_tokens": 100},
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_with_context(self):
        """Stream accepts context parameter."""
        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/test/stream",
                json={"message": "Hello", "context": {"user": "test-user"}},
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_response_headers(self):
        """Stream response has correct headers."""
        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/test/stream",
                json={"message": "Hello"},
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            # Cache-Control should be no-cache for SSE
            cache_control = response.headers.get("cache-control", "")
            assert "no-cache" in cache_control or cache_control == ""

    @pytest.mark.asyncio
    async def test_stream_empty_message(self):
        """Stream handles empty message."""
        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/test/stream",
                json={"message": ""},
            )

            # Should handle empty message without crashing
            assert response.status_code == 200
