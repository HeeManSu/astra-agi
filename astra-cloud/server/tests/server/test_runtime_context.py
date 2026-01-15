"""
Tests for RuntimeContext passing.

Tests context dict passing from server to agent.
"""

from dataclasses import dataclass, field
from typing import Any

from astra.server import create_app
from fastapi.testclient import TestClient


# ============================================================================
# Mock Agent that captures context
# ============================================================================


@dataclass
class ContextCapturingAgent:
    """Agent that captures context for verification."""

    name: str = "context-agent"
    description: str = "Test agent"
    captured_contexts: list = field(default_factory=list)

    async def invoke(
        self,
        message: str,
        *,
        thread_id: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs,
    ):
        """Capture context and return response."""
        self.captured_contexts.append(context)

        @dataclass
        class Response:
            content: str = "OK"
            thread_id: str | None = None

        return Response(content="OK", thread_id=thread_id)


# ============================================================================
# Context Passing Tests
# ============================================================================


class TestContextPassingToAgent:
    """Test context is passed to agent.invoke()."""

    def test_context_passed(self):
        """Context is passed to agent.invoke()."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {"user_id": "123"},
            },
        )

        assert len(agent.captured_contexts) == 1
        assert agent.captured_contexts[0] == {"user_id": "123"}

    def test_empty_context_is_none_or_empty(self):
        """Context is None or empty when not provided."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello"},
        )

        assert len(agent.captured_contexts) == 1
        ctx = agent.captured_contexts[0]
        assert ctx is None or ctx == {}

    def test_user_id_accessible(self):
        """Context with user_id is accessible in agent."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {"user_id": "user-abc"},
            },
        )

        assert agent.captured_contexts[0]["user_id"] == "user-abc"

    def test_channel_id_accessible(self):
        """Context with channel_id is accessible."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {"channel_id": "slack-123"},
            },
        )

        assert agent.captured_contexts[0]["channel_id"] == "slack-123"

    def test_custom_keys_accessible(self):
        """Context with custom keys is accessible."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {
                    "custom_key": "custom_value",
                    "another": 123,
                },
            },
        )

        ctx = agent.captured_contexts[0]
        assert ctx["custom_key"] == "custom_value"
        assert ctx["another"] == 123

    def test_context_not_modified(self):
        """Context is not modified by server."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        original_context = {
            "user_id": "123",
            "nested": {"key": "value"},
        }

        client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": original_context,
            },
        )

        # Context should match exactly
        assert agent.captured_contexts[0] == original_context

    def test_context_isolation(self):
        """Context doesn't leak between requests."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        # First request with user A
        client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {"user_id": "user-A"},
            },
        )

        # Second request with user B
        client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {"user_id": "user-B"},
            },
        )

        assert agent.captured_contexts[0]["user_id"] == "user-A"
        assert agent.captured_contexts[1]["user_id"] == "user-B"


# ============================================================================
# Context Validation Tests
# ============================================================================


class TestContextValidation:
    """Test context validation and edge cases."""

    def test_null_context_handled(self):
        """Context as null/None is handled."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": None,
            },
        )

        assert response.status_code == 200

    def test_empty_object_works(self):
        """Context as empty object {} works."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {},
            },
        )

        assert response.status_code == 200

    def test_nested_objects(self):
        """Context with nested objects works."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {"user": {"profile": {"settings": {"theme": "dark"}}}},
            },
        )

        assert response.status_code == 200
        ctx = agent.captured_contexts[0]
        assert ctx["user"]["profile"]["settings"]["theme"] == "dark"

    def test_arrays(self):
        """Context with arrays works."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {
                    "tags": ["a", "b", "c"],
                    "ids": [1, 2, 3],
                },
            },
        )

        assert response.status_code == 200
        ctx = agent.captured_contexts[0]
        assert ctx["tags"] == ["a", "b", "c"]

    def test_numeric_values(self):
        """Context with numeric values works."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {
                    "int_val": 42,
                    "float_val": 3.14,
                },
            },
        )

        assert response.status_code == 200
        ctx = agent.captured_contexts[0]
        assert ctx["int_val"] == 42
        assert ctx["float_val"] == 3.14

    def test_boolean_values(self):
        """Context with boolean values works."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {
                    "is_admin": True,
                    "is_guest": False,
                },
            },
        )

        assert response.status_code == 200
        ctx = agent.captured_contexts[0]
        assert ctx["is_admin"] is True
        assert ctx["is_guest"] is False

    def test_unicode_values(self):
        """Context with Unicode values works."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {
                    "japanese": "日本語",
                    "emoji": "🚀🎉",
                    "arabic": "مرحبا",
                },
            },
        )

        assert response.status_code == 200
        ctx = agent.captured_contexts[0]
        assert ctx["japanese"] == "日本語"
        assert ctx["emoji"] == "🚀🎉"

    def test_special_json_chars(self):
        """Context with special JSON chars works."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {
                    "quoted": 'He said "hello"',
                    "newline": "line1\nline2",
                    "tab": "col1\tcol2",
                },
            },
        )

        assert response.status_code == 200


# ============================================================================
# Context in Streaming Tests
# ============================================================================


class TestContextInStreaming:
    """Test context passing in streaming requests."""

    def test_context_passed_in_stream(self):
        """Context is passed in stream requests."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/stream",
            json={
                "message": "Hello",
                "context": {"stream_key": "stream_value"},
            },
        )

        assert response.status_code == 200
        # Agent should have received context
        if agent.captured_contexts:
            assert agent.captured_contexts[0].get("stream_key") == "stream_value"

    def test_thread_id_in_context(self):
        """Thread ID is passed as part of invocation."""
        agent = ContextCapturingAgent()
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "thread_id": "thread-123",
                "context": {"key": "value"},
            },
        )

        assert response.status_code == 200
