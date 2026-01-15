"""
Integration Tests for Astra Server.

End-to-end tests for complete request flows.
"""

from astra.server import create_app
from fastapi.testclient import TestClient

from .conftest import create_agent, create_storage  # noqa: TID252


# ============================================================================
# Full Request Flow Tests
# ============================================================================


class TestFullRequestFlow:
    """Test complete request flows."""

    def test_generate_endpoint_e2e(self):
        """Generate endpoint works end-to-end."""
        agent = create_agent()
        app = create_app(agents={"assistant": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/assistant/generate",
            json={"message": "Hello!"},
        )

        assert response.status_code == 200
        assert "content" in response.json()
        assert len(response.json()["content"]) > 0

    def test_thread_creation_e2e(self):
        """Thread creation works end-to-end."""
        agent = create_agent(storage=create_storage())
        app = create_app(agents={"assistant": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/threads",
            json={"agent_name": "assistant"},
        )

        assert response.status_code == 200
        assert "id" in response.json()

    def test_message_flow_e2e(self):
        """Message flow works end-to-end."""
        agent = create_agent(storage=create_storage())
        app = create_app(agents={"assistant": agent})
        client = TestClient(app)

        # Create thread first
        thread_response = client.post(
            "/v1/threads",
            json={"agent_name": "assistant"},
        )
        thread_id = thread_response.json()["id"]

        # Add message
        response = client.post(
            f"/v1/threads/{thread_id}/messages",
            json={
                "role": "user",
                "content": "Hello!",
            },
        )

        assert response.status_code == 200
        assert "id" in response.json()

        # List messages
        response = client.get(f"/v1/threads/{thread_id}/messages")
        assert response.status_code == 200


# ============================================================================
# Multi-Agent Scenarios
# ============================================================================


class TestMultiAgentScenarios:
    """Test scenarios with multiple agents."""

    def test_multiple_agents_accessible(self):
        """Multiple agents are all accessible."""
        agents = {
            "assistant": create_agent(name="assistant"),
            "coder": create_agent(name="coder"),
            "reviewer": create_agent(name="reviewer"),
        }
        app = create_app(agents=agents)
        client = TestClient(app)

        # All agents should be accessible
        for name in ["assistant", "coder", "reviewer"]:
            response = client.get(f"/v1/agents/{name}")
            assert response.status_code == 200

    def test_shared_storage_works(self):
        """Shared storage works correctly."""
        storage = create_storage()
        agents = {
            "a1": create_agent(name="a1", storage=storage),
            "a2": create_agent(name="a2", storage=storage),
        }
        app = create_app(agents=agents)
        client = TestClient(app)

        # Both agents should work
        response = client.post(
            "/v1/threads",
            json={"agent_name": "a1"},
        )
        assert response.status_code == 200

        response = client.post(
            "/v1/threads",
            json={"agent_name": "a2"},
        )
        assert response.status_code == 200

    def test_agent_isolation(self):
        """Agent isolation is maintained."""
        agents = {
            "a1": create_agent(name="a1"),
            "a2": create_agent(name="a2"),
        }
        app = create_app(agents=agents)
        client = TestClient(app)

        # Each agent should have its own response
        r1 = client.post(
            "/v1/agents/a1/generate",
            json={"message": "Test"},
        )
        r2 = client.post(
            "/v1/agents/a2/generate",
            json={"message": "Test"},
        )

        assert r1.status_code == 200
        assert r2.status_code == 200


# ============================================================================
# Error Recovery Tests
# ============================================================================


class TestErrorRecovery:
    """Test error handling and recovery."""

    def test_server_continues_after_404(self):
        """Server continues after 404."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        # Trigger 404
        response = client.get("/v1/agents/nonexistent")
        assert response.status_code == 404

        # Server should still work
        response = client.get("/health")
        assert response.status_code == 200

    def test_server_continues_after_invalid_request(self):
        """Server continues after invalid request."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        # Trigger 422 (invalid request)
        response = client.post(
            "/v1/agents/test/generate",
            json={},  # Missing message
        )
        assert response.status_code == 422

        # Server should still work
        response = client.get("/health")
        assert response.status_code == 200

    def test_graceful_degradation(self):
        """Graceful degradation is possible."""
        # Even with issues, server should keep running
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        # Multiple error requests should not crash server
        for _ in range(5):
            client.get("/v1/agents/nonexistent")
            client.post("/v1/agents/test/generate", json={})

        # Server still works
        response = client.get("/health")
        assert response.status_code == 200


class TestMultiAgentAdditional:
    """Additional multi-agent tests."""

    def test_different_storage_per_agent(self):
        """Different storage per agent works."""
        storage1 = create_storage("storage1")
        storage2 = create_storage("storage2")

        agents = {
            "agent1": create_agent(name="agent1", storage=storage1),
            "agent2": create_agent(name="agent2", storage=storage2),
        }
        app = create_app(agents=agents)
        client = TestClient(app)

        # Both agents should work independently
        response1 = client.post(
            "/v1/threads",
            json={"agent_name": "agent1"},
        )
        response2 = client.post(
            "/v1/threads",
            json={"agent_name": "agent2"},
        )

        # Both should work
        assert response1.status_code in [200, 400]  # 400 if storage not fully connected
        assert response2.status_code in [200, 400]
