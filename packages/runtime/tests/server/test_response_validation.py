"""
Generate Response Validation Tests for Astra Server.

Tests response fields like usage, tool_calls, and content formatting.
"""

from astra.server import create_app
from fastapi.testclient import TestClient

from .conftest import create_agent  # noqa: TID252


# ============================================================================
# Test Setup
# ============================================================================


def create_test_app(**kwargs):
    """Create a test app with default agent."""
    agent = kwargs.pop("agent", create_agent())
    agents = kwargs.pop("agents", {"test": agent})
    return create_app(agents=agents, **kwargs)


# ============================================================================
# Response Structure Tests
# ============================================================================


class TestGenerateResponseStructure:
    """Test generate response structure."""

    def test_response_has_content_field(self):
        """Response includes content field."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello"},
        )

        assert response.status_code == 200
        assert "content" in response.json()

    def test_response_content_is_string(self):
        """Response content is a string."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello"},
        )

        assert isinstance(response.json()["content"], str)

    def test_response_content_not_empty(self):
        """Response content is not empty."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello"},
        )

        assert len(response.json()["content"]) > 0

    def test_response_includes_thread_id_when_provided(self):
        """Response includes thread_id when provided in request."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello", "thread_id": "test-thread-123"},
        )

        assert response.status_code == 200
        assert response.json().get("thread_id") == "test-thread-123"


# ============================================================================
# Usage Info Tests
# ============================================================================


class TestGenerateUsageInfo:
    """Test usage info in generate response."""

    def test_response_may_include_usage(self):
        """Response may include usage field."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello"},
        )

        # Usage is optional - just verify structure if present
        if "usage" in response.json() and response.json()["usage"]:
            usage = response.json()["usage"]
            assert "prompt_tokens" in usage or "total_tokens" in usage

    def test_usage_has_valid_structure(self):
        """Usage has expected fields when present."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello"},
        )

        # If usage is present, validate structure
        if response.json().get("usage"):
            usage = response.json()["usage"]
            # At minimum should have token counts
            for field in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                if field in usage:
                    assert isinstance(usage[field], int)
                    assert usage[field] >= 0


# ============================================================================
# Tool Calls Tests
# ============================================================================


class TestGenerateToolCalls:
    """Test tool calls in generate response."""

    def test_response_may_include_tool_calls(self):
        """Response may include tool_calls field."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello"},
        )

        # Tool calls are optional
        assert response.status_code == 200
        # If present, should be a list
        if "tool_calls" in response.json() and response.json()["tool_calls"]:
            assert isinstance(response.json()["tool_calls"], list)


# ============================================================================
# Parameter Validation Tests
# ============================================================================


class TestGenerateParameters:
    """Test generate request parameters."""

    def test_temperature_parameter_accepted(self):
        """Temperature parameter is accepted."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello", "temperature": 0.7},
        )

        assert response.status_code == 200

    def test_temperature_zero_accepted(self):
        """Temperature of 0 is accepted."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello", "temperature": 0.0},
        )

        assert response.status_code == 200

    def test_temperature_max_accepted(self):
        """Temperature at max (2.0) is accepted."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello", "temperature": 2.0},
        )

        assert response.status_code == 200

    def test_temperature_above_max_rejected(self):
        """Temperature above max is rejected."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello", "temperature": 2.5},
        )

        assert response.status_code == 422  # Validation error

    def test_temperature_negative_rejected(self):
        """Negative temperature is rejected."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello", "temperature": -0.5},
        )

        assert response.status_code == 422

    def test_max_tokens_parameter_accepted(self):
        """max_tokens parameter is accepted."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello", "max_tokens": 100},
        )

        assert response.status_code == 200

    def test_max_tokens_zero_rejected(self):
        """max_tokens of 0 is rejected."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello", "max_tokens": 0},
        )

        assert response.status_code == 422

    def test_max_tokens_negative_rejected(self):
        """Negative max_tokens is rejected."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello", "max_tokens": -100},
        )

        assert response.status_code == 422


# ============================================================================
# Edge Cases
# ============================================================================


class TestGenerateEdgeCases:
    """Test edge cases for generate endpoint."""

    def test_message_with_only_whitespace(self):
        """Whitespace-only message is handled."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "   "},
        )

        # Should either succeed or return 400, not crash
        assert response.status_code in [200, 400]

    def test_message_with_null_bytes(self):
        """Message with null bytes is handled."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello\x00World"},
        )

        assert response.status_code in [200, 400]

    def test_context_with_special_keys(self):
        """Context with special key names is handled."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {
                    "__proto__": "test",
                    "constructor": "val",
                    "$set": {"key": "val"},
                },
            },
        )

        # Should handle without security issues
        assert response.status_code == 200
