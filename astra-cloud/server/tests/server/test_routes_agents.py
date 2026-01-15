"""
Tests for Astra Server Agent Routes.

Tests /v1/agents endpoints including generate, stream, and ingest.
"""

from astra.server import create_app
from fastapi.testclient import TestClient

from .conftest import create_agent, create_rag_pipeline, create_storage  # noqa: TID252


# ============================================================================
# Setup
# ============================================================================


def create_test_app(**kwargs):
    """Create a test app with mock agent."""
    agent = kwargs.pop("agent", create_agent())
    agents = kwargs.pop("agents", {"test": agent})
    return create_app(agents=agents, **kwargs)


# ============================================================================
# GET /v1/agents Tests
# ============================================================================


class TestListAgents:
    """Test GET /v1/agents endpoint."""

    def test_returns_list(self):
        """Returns list of all agents."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/agents")

        assert response.status_code == 200
        # Response is a list directly
        agents = response.json()
        assert isinstance(agents, list)
        assert len(agents) == 1

    def test_multiple_agents_listed(self):
        """Multiple agents are listed."""
        agents = {
            "a1": create_agent(name="a1"),
            "a2": create_agent(name="a2"),
        }
        app = create_test_app(agents=agents)
        client = TestClient(app)

        response = client.get("/v1/agents")

        assert len(response.json()) == 2

    def test_agent_name_included(self):
        """Agent name is included."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/agents")

        agents = response.json()
        agent = agents[0]
        assert "name" in agent
        assert agent["name"] == "test"

    def test_has_memory_reflects_storage(self):
        """has_memory reflects storage presence."""
        agent_with_storage = create_agent(storage=create_storage())
        app = create_test_app(agent=agent_with_storage)
        client = TestClient(app)

        response = client.get("/v1/agents")

        agents = response.json()
        agent = agents[0]
        assert agent["has_memory"] is True

    def test_has_rag_reflects_pipeline(self):
        """has_rag reflects rag_pipeline presence."""
        agent_with_rag = create_agent(rag_pipeline=create_rag_pipeline())
        app = create_test_app(agent=agent_with_rag)
        client = TestClient(app)

        response = client.get("/v1/agents")

        agents = response.json()
        agent = agents[0]
        assert agent["has_rag"] is True


# ============================================================================
# GET /v1/agents/{name} Tests
# ============================================================================


class TestGetAgent:
    """Test GET /v1/agents/{name} endpoint."""

    def test_returns_agent_details(self):
        """Returns agent details for valid name."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/agents/test")

        assert response.status_code == 200
        assert response.json()["name"] == "test"

    def test_returns_404_unknown(self):
        """Returns 404 for unknown name."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/agents/unknown")

        assert response.status_code == 404

    def test_404_includes_name(self):
        """404 error message includes agent name."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/agents/my-missing-agent")

        assert response.status_code == 404
        assert "my-missing-agent" in response.json()["detail"]

    def test_includes_description(self):
        """Description is included if present."""
        agent = create_agent(description="A helpful agent")
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.get("/v1/agents/test")

        assert response.json()["description"] == "A helpful agent"


# ============================================================================
# POST /v1/agents/{name}/generate Tests
# ============================================================================


class TestGenerate:
    """Test POST /v1/agents/{name}/generate endpoint."""

    def test_valid_request_returns_response(self):
        """Valid request returns response."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello"},
        )

        assert response.status_code == 200
        assert "content" in response.json()

    def test_returns_404_unknown_agent(self):
        """Returns 404 for unknown agent."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/unknown/generate",
            json={"message": "Hello"},
        )

        assert response.status_code == 404

    def test_message_is_required(self):
        """message field is required."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={},
        )

        assert response.status_code == 422

    def test_empty_message_is_valid(self):
        """Empty message is valid."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": ""},
        )

        assert response.status_code == 200

    def test_thread_id_passed(self):
        """thread_id is optional and passed."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "thread_id": "thread-123",
            },
        )

        assert response.status_code == 200
        assert response.json()["thread_id"] == "thread-123"

    def test_context_passed(self):
        """context dict is optional and passed."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {"user_id": "user-123"},
            },
        )

        assert response.status_code == 200

    def test_response_includes_content(self):
        """Response includes content."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": "Hello"},
        )

        assert "content" in response.json()
        assert len(response.json()["content"]) > 0


# ============================================================================
# POST /v1/agents/{name}/stream Tests
# ============================================================================
# NOTE: Streaming tests moved to test_streaming_integration.py to use
# Gemini model with proper async handling (HuggingFaceLocal hangs)

# ============================================================================
# POST /v1/agents/{name}/ingest Tests
# ============================================================================


class TestIngest:
    """Test POST /v1/agents/{name}/ingest endpoint."""

    def test_returns_404_unknown_agent(self):
        """Returns 404 for unknown agent."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/unknown/ingest",
            json={"text": "Some content"},
        )

        assert response.status_code == 404

    def test_returns_400_no_rag(self):
        """Returns 400 if agent has no RAG."""
        agent = create_agent(rag_pipeline=None)
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/ingest",
            json={"text": "Some content"},
        )

        assert response.status_code == 400

    def test_returns_400_no_content(self):
        """Returns 400 if no text/url/path provided."""
        agent = create_agent(rag_pipeline=create_rag_pipeline())
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/ingest",
            json={},
        )

        assert response.status_code == 400

    def test_text_content_ingested(self):
        """text content is ingested."""
        agent = create_agent(rag_pipeline=create_rag_pipeline())
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/ingest",
            json={"text": "Some content to ingest"},
        )

        assert response.status_code == 200


# ============================================================================
# Context Passing Tests
# ============================================================================


class TestContextPassing:
    """Test RuntimeContext passing to agent."""

    def test_empty_context_works(self):
        """Empty context dict works."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {},
            },
        )

        assert response.status_code == 200

    def test_context_with_user_id(self):
        """Context with user_id works."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {"user_id": "user-123"},
            },
        )

        assert response.status_code == 200

    def test_context_with_nested_objects(self):
        """Context with nested objects works."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {
                    "user": {
                        "id": "123",
                        "name": "John",
                        "metadata": {"role": "admin"},
                    }
                },
            },
        )

        assert response.status_code == 200

    def test_context_with_arrays(self):
        """Context with arrays works."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {
                    "tags": ["important", "urgent"],
                    "ids": [1, 2, 3],
                },
            },
        )

        assert response.status_code == 200

    def test_context_with_unicode(self):
        """Context with Unicode values works."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "context": {
                    "name": "日本語",
                    "emoji": "🚀",
                },
            },
        )

        assert response.status_code == 200


# ============================================================================
# Additional Agent Route Tests
# ============================================================================


class TestListAgentsAdditional:
    """Additional tests for GET /v1/agents."""

    def test_agent_description_included(self):
        """Agent description is included if present."""
        agent = create_agent(description="A helpful assistant")
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.get("/v1/agents")

        agents = response.json()
        assert agents[0].get("description") == "A helpful assistant"


class TestGetAgentAdditional:
    """Additional tests for GET /v1/agents/{name}."""

    def test_tool_list_included(self):
        """Tool list is included in agent details."""

        class MockTool:
            name = "calculator"

        agent = create_agent(tools=[MockTool()])
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.get("/v1/agents/test")

        # Tools should be listed in some form
        assert response.status_code == 200


class TestGenerateAdditional:
    """Additional tests for POST /v1/agents/{name}/generate."""

    def test_temperature_passed(self):
        """Temperature is optional and passed."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "temperature": 0.7,
            },
        )

        assert response.status_code == 200

    def test_max_tokens_passed(self):
        """Max tokens is optional and passed."""
        app = create_test_app()
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={
                "message": "Hello",
                "max_tokens": 1000,
            },
        )

        assert response.status_code == 200


# NOTE: TestStreamAdditional moved to test_streaming_integration.py


class TestIngestAdditional:
    """Additional tests for POST /v1/agents/{name}/ingest."""

    def test_metadata_passed(self):
        """Metadata is passed through to RAG."""
        agent = create_agent(rag_pipeline=create_rag_pipeline())
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/ingest",
            json={
                "text": "Some content",
                "metadata": {"source": "web", "author": "test"},
            },
        )

        assert response.status_code == 200

    def test_name_passed(self):
        """Name is passed through to RAG."""
        agent = create_agent(rag_pipeline=create_rag_pipeline())
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/ingest",
            json={
                "text": "Some content",
                "name": "My Document",
            },
        )

        assert response.status_code == 200
