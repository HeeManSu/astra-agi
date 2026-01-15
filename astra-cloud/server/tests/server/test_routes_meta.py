"""
Tests for Astra Server Meta Routes.

Tests /v1/meta, /health, and /v1/providers endpoints.
"""

from astra.server import create_app
from fastapi.testclient import TestClient

from .conftest import (  # noqa: TID252
    create_agent,
    create_rag_pipeline,
    create_storage,
)


# ============================================================================
# Setup
# ============================================================================


def create_test_app(**kwargs):
    """Create a test app with mock agent."""
    agent = kwargs.pop("agent", create_agent())
    agents = kwargs.pop("agents", {"test": agent})
    return create_app(agents=agents, **kwargs)


# ============================================================================
# GET /v1/meta Tests
# ============================================================================


class TestGetMeta:
    """Test GET /v1/meta endpoint."""

    def test_returns_version(self):
        """Returns server version."""
        app = create_test_app(version="2.0.0")
        client = TestClient(app)

        response = client.get("/v1/meta")

        assert response.status_code == 200
        assert response.json()["version"] == "2.0.0"

    def test_returns_server_name(self):
        """Returns server name."""
        app = create_test_app(name="My Server")
        client = TestClient(app)

        response = client.get("/v1/meta")

        assert response.json()["server"]["name"] == "My Server"

    def test_returns_uptime(self):
        """Returns server uptime."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/meta")

        assert "uptime" in response.json()["server"]
        assert isinstance(response.json()["server"]["uptime"], int)

    def test_returns_agents_list(self):
        """Returns list of agents."""
        agents = {
            "agent1": create_agent(name="agent1"),
            "agent2": create_agent(name="agent2"),
        }
        app = create_test_app(agents=agents)
        client = TestClient(app)

        response = client.get("/v1/meta")

        agent_names = [a["name"] for a in response.json()["agents"]]
        assert "agent1" in agent_names
        assert "agent2" in agent_names

    def test_agent_info_includes_name(self):
        """Agent info includes name."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/meta")

        agents = response.json()["agents"]
        assert len(agents) >= 1
        assert "name" in agents[0]

    def test_agent_info_includes_endpoints(self):
        """Agent info includes endpoints."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/meta")

        agent = response.json()["agents"][0]
        assert "endpoints" in agent
        assert "generate" in agent["endpoints"]
        assert "stream" in agent["endpoints"]

    def test_agent_info_includes_features(self):
        """Agent info includes features."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/meta")

        agent = response.json()["agents"][0]
        assert "features" in agent
        assert "streaming" in agent["features"]

    def test_features_reflect_capabilities(self):
        """Features reflect actual agent capabilities."""
        agent = create_agent(
            storage=create_storage(),
            rag_pipeline=create_rag_pipeline(),
        )
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.get("/v1/meta")

        features = response.json()["agents"][0]["features"]
        assert features["memory"] is True
        assert features["rag"] is True

    def test_ingest_endpoint_null_without_rag(self):
        """ingest endpoint is null if no RAG."""
        agent = create_agent(rag_pipeline=None)
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.get("/v1/meta")

        endpoints = response.json()["agents"][0]["endpoints"]
        assert endpoints.get("ingest") is None


# ============================================================================
# GET /health Tests
# ============================================================================


class TestHealthCheck:
    """Test GET /health endpoint."""

    def test_returns_healthy(self):
        """Returns healthy when all OK."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_components_count_accurate(self):
        """Components count is accurate."""
        agent = create_agent(storage=create_storage())
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.get("/health")

        components = response.json()["components"]
        assert components["agents"] == 1
        assert components["storage"] >= 0

    def test_uptime_calculated(self):
        """Uptime is calculated correctly."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/health")

        assert "uptime" in response.json()
        assert response.json()["uptime"] >= 0


# ============================================================================
# GET /v1/providers Tests
# ============================================================================


class TestListProviders:
    """Test GET /v1/providers endpoint."""

    def test_returns_providers_list(self):
        """Returns list of providers."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/providers")

        assert response.status_code == 200
        assert "providers" in response.json()
        assert isinstance(response.json()["providers"], list)

    def test_discovers_from_agent_models(self):
        """Discovers providers from agent models."""
        agent = create_agent()
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.get("/v1/providers")

        # Should have discovered at least one provider
        assert len(response.json()["providers"]) > 0

    def test_includes_known_providers(self):
        """Includes known providers as defaults."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/providers")

        provider_ids = [p["id"] for p in response.json()["providers"]]
        assert "gemini" in provider_ids
        assert "bedrock" in provider_ids

    def test_no_duplicates(self):
        """No duplicates in list."""
        # Multiple agents with same model type
        agent1 = create_agent(name="agent1")
        agent2 = create_agent(name="agent2")
        app = create_test_app(agents={"a1": agent1, "a2": agent2})
        client = TestClient(app)

        response = client.get("/v1/providers")

        provider_ids = [p["id"] for p in response.json()["providers"]]
        # Check no duplicates
        assert len(provider_ids) == len(set(provider_ids))

    def test_provider_includes_fields(self):
        """Provider includes id, name, description."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/v1/providers")

        provider = response.json()["providers"][0]
        assert "id" in provider
        assert "name" in provider


# ============================================================================
# Additional Meta Route Tests
# ============================================================================


class TestHealthAdditional:
    """Additional health endpoint tests."""

    def test_health_returns_status_field(self):
        """Health endpoint returns status field."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/health")

        assert "status" in response.json()
        assert response.json()["status"] in ["healthy", "degraded", "unhealthy"]
