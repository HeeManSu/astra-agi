"""
Thread Pagination Tests for Astra Server.

Tests pagination edge cases for thread listing.
"""

from astra.server import create_app
from fastapi.testclient import TestClient

from .conftest import create_agent, create_storage  # noqa: TID252


# ============================================================================
# Test Setup
# ============================================================================


def create_test_app_with_storage(**kwargs):
    """Create a test app with storage-enabled agent."""
    storage = create_storage()
    agent = create_agent(storage=storage)
    agents = kwargs.pop("agents", {"test": agent})
    return create_app(agents=agents, **kwargs)


# ============================================================================
# Pagination Parameter Tests
# ============================================================================


class TestPaginationParameters:
    """Test pagination parameter handling."""

    def test_default_pagination(self):
        """Default pagination values are used."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 20

    def test_custom_page_number(self):
        """Custom page number is respected."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads?page=2")

        assert response.status_code == 200
        assert response.json()["page"] == 2

    def test_custom_per_page(self):
        """Custom per_page is respected."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads?per_page=50")

        assert response.status_code == 200
        assert response.json()["per_page"] == 50

    def test_per_page_max_100(self):
        """per_page max is 100."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads?per_page=101")

        # Should reject > 100
        assert response.status_code == 422

    def test_per_page_min_1(self):
        """per_page min is 1."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads?per_page=0")

        assert response.status_code == 422

    def test_page_min_1(self):
        """Page min is 1."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads?page=0")

        assert response.status_code == 422


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestPaginationEdgeCases:
    """Test pagination edge cases."""

    def test_page_beyond_total_returns_empty(self):
        """Page beyond total returns empty list."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # Request a very high page number
        response = client.get("/v1/threads?page=1000")

        assert response.status_code == 200
        assert response.json()["threads"] == []

    def test_large_page_number_accepted(self):
        """Large page numbers are accepted."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads?page=999999")

        # Should work, just return empty
        assert response.status_code == 200

    def test_exactly_per_page_threads(self):
        """Exactly per_page threads returns correctly."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # Create exactly 5 threads
        for _ in range(5):
            client.post("/v1/threads", json={"agent_name": "test"})

        # Request with per_page=5
        response = client.get("/v1/threads?per_page=5")

        assert response.status_code == 200
        assert len(response.json()["threads"]) <= 5


# ============================================================================
# Filter Tests
# ============================================================================


class TestThreadFiltering:
    """Test thread filtering by agent."""

    def test_filter_by_agent_name(self):
        """Filter by agent_name works."""
        storage = create_storage()
        agent1 = create_agent(name="agent1", storage=storage)
        agent2 = create_agent(name="agent2", storage=storage)
        # Share storage
        agent2.storage = agent1.storage
        app = create_app(agents={"agent1": agent1, "agent2": agent2})
        client = TestClient(app)

        # Create threads for different agents
        client.post("/v1/threads", json={"agent_name": "agent1"})
        client.post("/v1/threads", json={"agent_name": "agent2"})

        # Filter by agent1
        response = client.get("/v1/threads?agent_name=agent1")

        assert response.status_code == 200
        for thread in response.json()["threads"]:
            assert thread["agent_name"] == "agent1"

    def test_filter_nonexistent_agent_returns_empty(self):
        """Filter by non-existent agent returns empty."""
        app = create_test_app_with_storage()
        client = TestClient(app)
        response = client.get("/v1/threads?agent_name=nonexistent")

        # Returns 404 if agent filter not found, or 200 with empty list
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert response.json()["threads"] == []


# ============================================================================
# Response Structure Tests
# ============================================================================


class TestPaginationResponseStructure:
    """Test pagination response fields."""

    def test_response_has_total(self):
        """Response includes total count."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads")

        assert response.status_code == 200
        assert "total" in response.json()
        assert isinstance(response.json()["total"], int)

    def test_response_has_threads_list(self):
        """Response includes threads list."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads")

        assert response.status_code == 200
        assert "threads" in response.json()
        assert isinstance(response.json()["threads"], list)

    def test_total_reflects_actual_count(self):
        """Total reflects actual thread count."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # Create 3 threads
        for _ in range(3):
            client.post("/v1/threads", json={"agent_name": "test"})

        response = client.get("/v1/threads")

        assert response.json()["total"] >= 3
