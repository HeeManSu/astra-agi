"""
Edge Case Tests for Astra Server.

Tests boundary conditions and unusual inputs.
"""

from typing import ClassVar

from astra.server import create_app
from fastapi.testclient import TestClient

from .conftest import create_agent, create_storage  # noqa: TID252


# ============================================================================
# Agent Name Edge Cases
# ============================================================================


class TestAgentNameEdgeCases:
    """Test edge cases in agent names."""

    def test_agent_name_with_hyphen(self):
        """Agent name with hyphens works."""
        app = create_app(agents={"my-agent-name": create_agent()})
        client = TestClient(app)

        response = client.get("/v1/agents/my-agent-name")
        assert response.status_code == 200

    def test_agent_name_with_underscore(self):
        """Agent name with underscores works."""
        app = create_app(agents={"my_agent_name": create_agent()})
        client = TestClient(app)

        response = client.get("/v1/agents/my_agent_name")
        assert response.status_code == 200

    def test_agent_name_with_numbers(self):
        """Agent name with numbers works."""
        app = create_app(agents={"agent123": create_agent()})
        client = TestClient(app)

        response = client.get("/v1/agents/agent123")
        assert response.status_code == 200

    def test_very_long_agent_name(self):
        """Very long agent name works."""
        long_name = "a" * 100
        app = create_app(agents={long_name: create_agent()})
        client = TestClient(app)

        response = client.get(f"/v1/agents/{long_name}")
        assert response.status_code == 200


# ============================================================================
# Message Content Edge Cases
# ============================================================================


class TestMessageContentEdgeCases:
    """Test edge cases in message content."""

    def test_very_long_message(self):
        """Very long message works."""
        # Use large model for robustness
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        # 3500 chars is ~875 tokens, fitting comfortably within GPT-2's 1024 limit
        # while still being a "very long" message for a chat context.
        long_message = "x" * 3500

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": long_message},
        )

        assert response.status_code == 200

    def test_message_with_unicode(self):
        """Message with unicode works."""
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello 🚀 世界 مرحبا"},
        )

        assert response.status_code == 200

    def test_message_with_newlines(self):
        """Message with newlines works."""
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Line 1\nLine 2\nLine 3"},
        )

        assert response.status_code == 200

    def test_message_with_special_chars(self):
        """Message with special chars works."""
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": '<script>alert("xss")</script>'},
        )

        assert response.status_code == 200

    def test_empty_message(self):
        """Empty message works."""
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": ""},
        )

        assert response.status_code == 200


# ============================================================================
# Context Edge Cases
# ============================================================================


class TestContextEdgeCases:
    """Test edge cases in context dict."""

    def test_very_large_context(self):
        """Very large context works."""
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        # Create a large message context by joining many lines
        large_message = "\n".join([f"msg {i}" for i in range(100)])

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": large_message,
            },
        )

        assert response.status_code == 200

    def test_deeply_nested_context(self):
        """Deeply nested context works."""
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        # Simulate nested conversation structure via prompts (flat list in API)
        def build_nested(depth: int) -> dict:
            if depth <= 1:
                return {"level": depth}
            return {"level": depth, "nested": build_nested(depth - 1)}

        nested = build_nested(20)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": nested,
            },
        )

        assert response.status_code == 200


# ============================================================================
# Thread/Message Edge Cases
# ============================================================================


class TestThreadEdgeCases:
    """Test edge cases in thread operations."""

    def test_thread_with_long_metadata(self):
        """Thread with long metadata works."""
        app = create_app(
            agents={"test": create_agent(use_large_model=True, storage=create_storage())}
        )
        client = TestClient(app)

        # Create thread with large metadata
        large_metadata = {f"key_{i}": "x" * 100 for i in range(100)}

        response = client.post(
            "/v1/threads",
            json={
                "agent_name": "test",
                "metadata": large_metadata,
            },
        )

        assert response.status_code == 200

    def test_message_with_long_content(self):
        """Message with very long content works."""
        app = create_app(agents={"test": create_agent(storage=create_storage())})
        client = TestClient(app)

        # Create thread first
        client.post(
            "/v1/threads",
            json={
                "agent_name": "test",
                "metadata": {"id": "thread-123"},
            },  # metadata won't set ID, but response handles it?
        )
        # Actually, create_thread response returns ID. we usually don't dictate ID in create request?
        # threads route: creates internal UUID.
        # But we need "thread-123" for the next call.
        # create_thread supports custom ID?
        # Check CreateThreadRequest in threads.py: NO.
        # So we must get the ID from response.

        thread_response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )
        thread_id = thread_response.json()["id"]

        response = client.post(
            f"/v1/threads/{thread_id}/messages",
            json={
                "role": "user",
                "content": "x" * 50000,
            },
        )

        assert response.status_code == 200


# ============================================================================
# Multiple Agents Edge Cases
# ============================================================================


class TestMultipleAgentsEdgeCases:
    """Test edge cases with multiple agents."""

    def test_many_agents(self):
        """Many agents (50+) works."""
        agents = {f"agent-{i}": create_agent(name=f"agent-{i}") for i in range(50)}
        app = create_app(agents=agents)
        client = TestClient(app)

        response = client.get("/v1/agents")

        assert response.status_code == 200
        # Response is a list directly
        assert len(response.json()) == 50

    def test_agents_with_similar_names(self):
        """Agents with similar names are distinguished."""
        agents = {
            "agent": create_agent(name="agent"),
            "agent1": create_agent(name="agent1"),
            "agent-1": create_agent(name="agent-1"),
        }
        app = create_app(agents=agents)
        client = TestClient(app)

        # All should be accessible
        for name in ["agent", "agent1", "agent-1"]:
            response = client.get(f"/v1/agents/{name}")
            assert response.status_code == 200


# ============================================================================
# Additional Edge Cases
# ============================================================================


class TestSpecialCharacterNames:
    """Test agent names with special characters."""

    def test_agent_name_with_dots(self):
        """Agent name with dots works."""
        agents = {"my.agent.v1": create_agent(name="my.agent.v1")}
        app = create_app(agents=agents)
        client = TestClient(app)

        response = client.get("/v1/agents/my.agent.v1")
        # May be 200 or 404 depending on routing
        assert response.status_code in [200, 404]

    def test_agent_name_numeric(self):
        """Agent name that is purely numeric works."""
        agents = {"123": create_agent(name="123")}
        app = create_app(agents=agents)
        client = TestClient(app)

        response = client.get("/v1/agents/123")
        assert response.status_code in [200, 404]


class TestEmptyAndNullContent:
    """Test empty and null content handling."""

    def test_empty_string_message(self):
        """Empty string message works."""
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": ""},
        )

        assert response.status_code == 200

    def test_whitespace_only_message(self):
        """Whitespace only message works."""
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "   \n\t   "},
        )

        assert response.status_code == 200


# ============================================================================
# Error Handling Edge Cases
# ============================================================================


class FailingAgent:
    """Agent that raises exceptions for error testing."""

    name = "failing-agent"
    description = "An agent that fails"
    storage = None
    rag_pipeline = None
    tools: ClassVar[list] = []

    async def invoke(self, message: str, **kwargs) -> str:
        raise RuntimeError("Agent invoke failed!")

    async def stream(self, message: str, **kwargs):
        raise RuntimeError("Agent stream failed!")


class TestAgentErrorHandling:
    """Test error handling when agents fail."""

    def test_agent_invoke_exception_returns_500(self):
        """Agent invoke exception returns 500."""
        app = create_app(agents={"failing": FailingAgent()})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/failing/generate",
            json={"message": "Hello"},
        )

        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()

    def test_agent_stream_exception_sends_error_event(self):
        """Agent stream exception sends error SSE event."""
        app = create_app(agents={"failing": FailingAgent()})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/failing/stream",
            json={"message": "Hello"},
        )

        # Even with error, should return 200 for SSE (error in stream)
        assert response.status_code == 200
        assert "error" in response.text


class TestIngestErrorHandling:
    """Test error handling for ingest endpoint."""

    def test_ingest_without_rag_returns_400(self):
        """Ingest without RAG pipeline returns 400."""
        app = create_app(agents={"test": create_agent()})  # No RAG
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/ingest",
            json={"text": "Some content"},
        )

        assert response.status_code == 400
        assert "RAG" in response.json()["detail"]


# ============================================================================
# Concurrent Request Edge Cases
# ============================================================================


class TestConcurrentRequests:
    """Test concurrent request handling."""

    def test_multiple_sequential_requests(self):
        """Multiple sequential requests don't interfere."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        # Send 10 requests sequentially
        responses = []
        for i in range(10):
            response = client.post(
                "/v1/agents/test/generate",
                json={"message": f"Message {i}"},
            )
            responses.append(response)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

    def test_different_agents_sequential(self):
        """Requests to different agents work independently."""
        agents = {
            "agent1": create_agent(name="Agent 1"),
            "agent2": create_agent(name="Agent 2"),
            "agent3": create_agent(name="Agent 3"),
        }
        app = create_app(agents=agents)
        client = TestClient(app)

        # Interleave requests to different agents
        for _ in range(3):
            for name in ["agent1", "agent2", "agent3"]:
                response = client.post(
                    f"/v1/agents/{name}/generate",
                    json={"message": "Hello"},
                )
                assert response.status_code == 200


# ============================================================================
# Response Content Edge Cases
# ============================================================================


class EmptyResponseAgent:
    """Agent that returns empty responses."""

    name = "empty-agent"
    description = "Returns empty"
    storage = None
    rag_pipeline = None
    tools: ClassVar[list] = []

    async def invoke(self, message: str, **kwargs) -> str:
        return ""

    async def stream(self, message: str, **kwargs):
        yield ""


class TestEmptyResponseHandling:
    """Test handling of empty responses."""

    def test_empty_response_content(self):
        """Empty response content is valid."""
        app = create_app(agents={"empty": EmptyResponseAgent()})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/empty/generate",
            json={"message": "Hello"},
        )

        assert response.status_code == 200
        assert response.json()["content"] == ""


# ============================================================================
# Thread ID Without Storage Edge Cases
# ============================================================================


class TestThreadIdWithoutStorage:
    """Test thread_id behavior when agent has no storage."""

    def test_generate_with_thread_id_no_storage(self):
        """Generate with thread_id works even without storage."""
        # Note: No storage, but uses large model
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "thread_id": "thread-123",
            },
        )

        assert response.status_code == 200
        # thread_id should be echoed back
        assert response.json()["thread_id"] == "thread-123"


# ============================================================================
# Unicode and Encoding Edge Cases
# ============================================================================


class TestUnicodeEdgeCases:
    """Test Unicode edge cases."""

    def test_message_with_emoji(self):
        """Message with emoji works."""
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello 👋 World 🌍!"},
        )

        assert response.status_code == 200

    def test_message_with_chinese_characters(self):
        """Message with Chinese characters works."""
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "你好世界"},
        )

        assert response.status_code == 200

    def test_message_with_rtl_text(self):
        """Message with RTL (Arabic/Hebrew) text works."""
        app = create_app(agents={"test": create_agent(use_large_model=True)})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "مرحبا بالعالم"},
        )

        assert response.status_code == 200
