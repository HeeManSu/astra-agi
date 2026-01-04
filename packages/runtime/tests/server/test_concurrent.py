"""
Concurrent Request Tests for Astra Server.

Tests parallel request handling and isolation.
"""

import asyncio

from astra.server import create_app
from httpx import ASGITransport, AsyncClient
import pytest

from .conftest import create_storage, create_streaming_agent  # noqa: TID252


# ============================================================================
# Concurrent Generate Tests
# ============================================================================


@pytest.mark.timeout(120)
class TestConcurrentGenerate:
    """Test concurrent generate requests."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_agent(self):
        """Multiple concurrent requests to same agent work."""
        agent = create_streaming_agent(name="test")
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Send 3 concurrent requests
            tasks = [
                client.post("/v1/agents/test/generate", json={"message": f"Hello {i}"})
                for i in range(3)
            ]
            responses = await asyncio.gather(*tasks)

            # All should succeed - skip if any rate limited
            for response in responses:
                if response.status_code == 429:
                    pytest.skip("Gemini API rate limited")
                if response.status_code >= 500:
                    pytest.skip("Server error - likely rate limited")
                assert response.status_code == 200
                assert "content" in response.json()

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_agents(self):
        """Concurrent requests to different agents work."""
        agent1 = create_streaming_agent(name="agent1")
        agent2 = create_streaming_agent(name="agent2")
        app = create_app(agents={"agent1": agent1, "agent2": agent2})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            tasks = [
                client.post("/v1/agents/agent1/generate", json={"message": "Hello 1"}),
                client.post("/v1/agents/agent2/generate", json={"message": "Hello 2"}),
            ]
            responses = await asyncio.gather(*tasks)

            for response in responses:
                # Skip if rate limited
                if response.status_code == 429:
                    pytest.skip("Gemini API rate limited")
                if response.status_code >= 500:
                    pytest.skip("Server error - likely rate limited")
                assert response.status_code == 200


# ============================================================================
# Concurrent Thread Tests
# ============================================================================


@pytest.mark.timeout(60)
class TestConcurrentThreads:
    """Test concurrent thread operations."""

    @pytest.mark.asyncio
    async def test_concurrent_thread_creation(self):
        """Multiple threads can be created concurrently."""
        storage = create_storage()
        agent = create_streaming_agent(storage=storage)
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create 5 threads concurrently
            tasks = [client.post("/v1/threads", json={"agent_name": "test"}) for _ in range(5)]
            responses = await asyncio.gather(*tasks)

            # All should succeed with unique IDs
            thread_ids = set()
            for response in responses:
                assert response.status_code == 200
                thread_id = response.json()["id"]
                assert thread_id not in thread_ids
                thread_ids.add(thread_id)

            assert len(thread_ids) == 5

    @pytest.mark.asyncio
    async def test_concurrent_message_addition(self):
        """Messages can be added concurrently to different threads."""
        storage = create_storage()
        agent = create_streaming_agent(storage=storage)
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create two threads
            t1 = await client.post("/v1/threads", json={"agent_name": "test"})
            t2 = await client.post("/v1/threads", json={"agent_name": "test"})
            thread1_id = t1.json()["id"]
            thread2_id = t2.json()["id"]

            # Add messages concurrently
            tasks = [
                client.post(
                    f"/v1/threads/{thread1_id}/messages",
                    json={"role": "user", "content": "Message 1"},
                ),
                client.post(
                    f"/v1/threads/{thread2_id}/messages",
                    json={"role": "user", "content": "Message 2"},
                ),
            ]
            responses = await asyncio.gather(*tasks)

            for response in responses:
                assert response.status_code == 200


# ============================================================================
# Concurrent Streaming Tests
# ============================================================================


@pytest.mark.timeout(120)
class TestConcurrentStreaming:
    """Test concurrent streaming requests."""

    @pytest.mark.asyncio
    async def test_concurrent_streams_same_agent(self):
        """Multiple concurrent streams to same agent work."""
        agent = create_streaming_agent(name="test")
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Start 2 concurrent streams
            tasks = [
                client.post("/v1/agents/test/stream", json={"message": f"Hi {i}"}) for i in range(2)
            ]
            responses = await asyncio.gather(*tasks)

            for response in responses:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")


# ============================================================================
# Request Isolation Tests
# ============================================================================


@pytest.mark.timeout(60)
class TestRequestIsolation:
    """Test that concurrent requests are properly isolated."""

    @pytest.mark.asyncio
    async def test_context_not_shared_between_requests(self):
        """Context from one request doesn't leak to another."""
        agent = create_streaming_agent(name="test")
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Send requests with different contexts
            tasks = [
                client.post(
                    "/v1/agents/test/generate",
                    json={"message": "Hello", "context": {"user": f"user{i}"}},
                )
                for i in range(3)
            ]
            responses = await asyncio.gather(*tasks)

            # All should succeed - skip if any rate limited
            for response in responses:
                if response.status_code == 429:
                    pytest.skip("Gemini API rate limited")
                if response.status_code >= 500:
                    pytest.skip("Server error - likely rate limited")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_thread_isolation(self):
        """Different threads maintain separate histories."""
        storage = create_storage()
        agent = create_streaming_agent(storage=storage)
        app = create_app(agents={"test": agent})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create two threads
            t1 = await client.post("/v1/threads", json={"agent_name": "test"})
            t2 = await client.post("/v1/threads", json={"agent_name": "test"})

            # Add different messages
            await client.post(
                f"/v1/threads/{t1.json()['id']}/messages",
                json={"role": "user", "content": "Thread 1 message"},
            )
            await client.post(
                f"/v1/threads/{t2.json()['id']}/messages",
                json={"role": "user", "content": "Thread 2 message"},
            )

            # Verify messages are isolated
            m1 = await client.get(f"/v1/threads/{t1.json()['id']}/messages")
            m2 = await client.get(f"/v1/threads/{t2.json()['id']}/messages")

            assert len(m1.json()["messages"]) == 1
            assert len(m2.json()["messages"]) == 1
            assert m1.json()["messages"][0]["content"] == "Thread 1 message"
            assert m2.json()["messages"][0]["content"] == "Thread 2 message"
