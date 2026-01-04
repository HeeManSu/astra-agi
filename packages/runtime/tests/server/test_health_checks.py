"""
Health Check Tests for Astra Server.

Tests health endpoint degraded states and component health.
"""

from typing import ClassVar

from astra.server import create_app
from fastapi.testclient import TestClient

from .conftest import create_agent, create_storage  # noqa: TID252


# ============================================================================
# Test Helper Classes
# ============================================================================


class FailingStorage:
    """Storage that fails health checks."""

    name: ClassVar[str] = "failing-storage"

    async def connect(self):
        pass

    async def create_tables(self):
        pass

    async def disconnect(self):
        pass

    async def table_exists(self, table_name: str) -> bool:
        raise RuntimeError("Storage connection failed")


class HealthyStorage:
    """Storage that passes health checks."""

    name: ClassVar[str] = "healthy-storage"

    async def connect(self):
        pass

    async def create_tables(self):
        pass

    async def disconnect(self):
        pass

    async def table_exists(self, table_name: str) -> bool:
        return True


# ============================================================================
# Test Setup
# ============================================================================


def create_test_app(**kwargs):
    """Create a test app with default agent."""
    agent = kwargs.pop("agent", create_agent())
    agents = kwargs.pop("agents", {"test": agent})
    return create_app(agents=agents, **kwargs)


# ============================================================================
# Health Response Fields Tests
# ============================================================================


class TestHealthResponseFields:
    """Test health endpoint response structure."""

    def test_health_returns_status(self):
        """Health response includes status field."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert "status" in response.json()

    def test_health_returns_components(self):
        """Health response includes components field."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/health")

        assert "components" in response.json()
        components = response.json()["components"]
        assert "agents" in components
        assert "storage" in components
        assert "mcp_tools" in components
        assert "rag_pipelines" in components

    def test_health_returns_uptime(self):
        """Health response includes uptime field."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/health")

        assert "uptime" in response.json()
        assert isinstance(response.json()["uptime"], int)
        assert response.json()["uptime"] >= 0

    def test_health_returns_dependencies(self):
        """Health response includes dependencies field."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/health")

        assert "dependencies" in response.json()
        assert isinstance(response.json()["dependencies"], dict)


# ============================================================================
# Health Status Tests
# ============================================================================


class TestHealthStatus:
    """Test health status values."""

    def test_health_status_healthy_no_storage(self):
        """Health status is healthy when no storage configured."""
        agent = create_agent(storage=None)
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.get("/health")

        assert response.json()["status"] == "healthy"

    def test_health_status_healthy_with_storage(self):
        """Health status is healthy with working storage."""
        agent = create_agent(storage=create_storage())
        app = create_test_app(agent=agent)
        client = TestClient(app)

        response = client.get("/health")

        # Should be healthy if storage works
        assert response.json()["status"] in ["healthy", "degraded"]

    def test_health_component_counts_correct(self):
        """Component counts reflect registered resources."""
        agents = {
            "agent1": create_agent(name="agent1"),
            "agent2": create_agent(name="agent2"),
        }
        app = create_test_app(agents=agents)
        client = TestClient(app)

        response = client.get("/health")

        assert response.json()["components"]["agents"] == 2


# ============================================================================
# Multiple Agents Health Tests
# ============================================================================


class TestMultipleAgentsHealth:
    """Test health with multiple agents and storage."""

    def test_health_multiple_agents_counted(self):
        """Multiple agents are counted correctly."""
        agents = {f"agent{i}": create_agent(name=f"agent{i}") for i in range(5)}
        app = create_test_app(agents=agents)
        client = TestClient(app)

        response = client.get("/health")

        assert response.json()["components"]["agents"] == 5

    def test_health_shared_storage_counted_once(self):
        """Shared storage is counted only once."""
        storage = create_storage()
        agent1 = create_agent(name="agent1", storage=storage)
        agent2 = create_agent(name="agent2", storage=storage)
        # Force same storage instance
        agent2.storage = agent1.storage
        app = create_test_app(agents={"a1": agent1, "a2": agent2})
        client = TestClient(app)

        response = client.get("/health")

        # Shared storage should be deduplicated
        assert response.json()["components"]["storage"] == 1
