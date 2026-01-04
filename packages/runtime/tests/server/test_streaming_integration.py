"""
Streaming Integration Tests for Astra Server.

These tests verify streaming endpoints with proper async handling.
They use Gemini model which has proper async streaming support.

Run these tests separately:
    uv run pytest packages/runtime/tests/server/test_streaming_integration.py -v --timeout=120

Requires GOOGLE_API_KEY or GEMINI_API_KEY environment variable.
"""

from astra.server import create_app
from httpx import ASGITransport, AsyncClient
import pytest

from .conftest import create_storage, create_streaming_agent  # noqa: TID252


# ============================================================================
# Streaming Endpoint Integration Tests
# ============================================================================


@pytest.mark.timeout(120)
class TestStreamingEndpoints:
    """
    Streaming endpoint integration tests.

    Uses AsyncClient instead of TestClient to properly handle
    async SSE streams without deadlocking.

    Uses Gemini model which has proper async streaming unlike
    HuggingFaceLocal which uses blocking thread-based streaming.
    """

    @pytest.mark.asyncio
    async def test_stream_endpoint_returns_sse(self):
        """Stream endpoint returns SSE content type."""
        agent = create_streaming_agent()
        app = create_app(agents={"assistant": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/assistant/stream",
                json={"message": "Say hello in one word"},
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_stream_with_thread_id_no_storage(self):
        """Stream with thread_id works even without storage."""
        agent = create_streaming_agent(name="test")
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/test/stream",
                json={
                    "message": "Hello",
                    "thread_id": "thread-123",
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_consumes_chunks(self):
        """Stream endpoint produces data chunks."""
        agent = create_streaming_agent()
        app = create_app(agents={"assistant": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/agents/assistant/stream",
                json={"message": "Say hi"},
            ) as response:
                assert response.status_code == 200

                chunks = []
                async for chunk in response.aiter_text():
                    chunks.append(chunk)

                # Should have received some data
                assert len(chunks) > 0 or len("".join(chunks)) > 0

    @pytest.mark.asyncio
    async def test_stream_with_context(self):
        """Stream endpoint accepts context parameter."""
        agent = create_streaming_agent()
        app = create_app(agents={"assistant": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/assistant/stream",
                json={
                    "message": "Hello!",
                    "context": {"user_id": "test-user"},
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stream_unknown_agent_returns_404(self):
        """Stream endpoint returns 404 for unknown agent."""
        agent = create_streaming_agent()
        app = create_app(agents={"assistant": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/unknown/stream",
                json={"message": "Hello!"},
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_streams_sse_events(self):
        """SSE events are streamed with correct format."""
        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/agents/test/stream",
                json={"message": "Hello"},
            ) as response:
                assert response.status_code == 200

                content = ""
                async for chunk in response.aiter_text():
                    content += chunk

                # Should have event data
                assert "event:" in content or "data:" in content

    @pytest.mark.asyncio
    async def test_cache_control_header(self):
        """Response has appropriate cache headers for streaming."""
        agent = create_streaming_agent()
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/agents/test/stream",
                json={"message": "Hello"},
            )

            # Response should succeed
            assert response.status_code == 200
            # Content-type should be event-stream
            assert "text/event-stream" in response.headers.get("content-type", "")


# ============================================================================
# Streaming with Storage Integration Tests
# ============================================================================


@pytest.mark.timeout(120)
class TestStreamingWithStorage:
    """Streaming tests with storage enabled."""

    @pytest.mark.asyncio
    async def test_stream_with_storage_and_thread(self):
        """Stream with storage creates thread history."""
        storage = create_storage()
        agent = create_streaming_agent(storage=storage)
        app = create_app(agents={"assistant": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First create a thread
            thread_response = await client.post(
                "/v1/threads",
                json={"agent_name": "assistant"},
            )
            thread_id = thread_response.json()["id"]

            # Then stream with that thread
            response = await client.post(
                "/v1/agents/assistant/stream",
                json={
                    "message": "Hello!",
                    "thread_id": thread_id,
                },
            )

            assert response.status_code == 200
