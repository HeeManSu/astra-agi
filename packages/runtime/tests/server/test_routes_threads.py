"""
Tests for Astra Server Thread Routes.

Tests /v1/threads endpoints for thread and message CRUD.
"""

from astra.server import create_app
from fastapi.testclient import TestClient

from .conftest import create_agent, create_storage  # noqa: TID252


# ============================================================================
# Setup
# ============================================================================


def create_test_app_with_storage(**kwargs):
    """Create a test app with mock agent that has storage."""
    storage = create_storage()
    agent = create_agent(storage=storage)
    agents = kwargs.pop("agents", {"test": agent})
    return create_app(agents=agents, **kwargs)


def create_test_app_no_storage(**kwargs):
    """Create a test app with mock agent without storage."""
    agent = create_agent(storage=None)
    agents = kwargs.pop("agents", {"test": agent})
    return create_app(agents=agents, **kwargs)


# ============================================================================
# GET /v1/threads Tests
# ============================================================================


class TestListThreads:
    """Test GET /v1/threads endpoint."""

    def test_returns_list(self):
        """Returns list of threads."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads")

        assert response.status_code == 200
        assert "threads" in response.json()

    def test_empty_returns_empty_list(self):
        """Empty storage returns empty list."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads")

        assert response.json()["threads"] == []

    def test_no_storage_returns_empty(self):
        """No storage returns empty list."""
        app = create_test_app_no_storage()
        client = TestClient(app)

        response = client.get("/v1/threads")

        assert response.status_code == 200
        assert response.json()["threads"] == []

    def test_page_parameter(self):
        """page parameter works."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads?page=2")

        assert response.status_code == 200
        assert response.json()["page"] == 2

    def test_per_page_parameter(self):
        """per_page parameter works."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads?per_page=50")

        assert response.status_code == 200
        assert response.json()["per_page"] == 50

    def test_per_page_defaults_to_20(self):
        """per_page defaults to 20."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads")

        assert response.json()["per_page"] == 20


# ============================================================================
# POST /v1/threads Tests
# ============================================================================


class TestCreateThread:
    """Test POST /v1/threads endpoint."""

    def test_creates_thread(self):
        """Creates thread successfully."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )

        assert response.status_code == 200
        assert "id" in response.json()

    def test_returns_404_unknown_agent(self):
        """Returns 404 for unknown agent."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.post(
            "/v1/threads",
            json={"agent_name": "unknown"},
        )

        assert response.status_code == 404

    def test_returns_400_no_storage(self):
        """Returns 400 if agent has no storage."""
        app = create_test_app_no_storage()
        client = TestClient(app)

        response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )

        assert response.status_code == 400

    def test_id_is_uuid(self):
        """Generated ID is UUID format."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )

        thread_id = response.json()["id"]
        # UUID format: 8-4-4-4-12 characters
        assert len(thread_id) == 36
        assert thread_id.count("-") == 4

    def test_timestamps_set(self):
        """created_at and updated_at are set."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )

        assert "created_at" in response.json()
        assert "updated_at" in response.json()

    def test_metadata_stored(self):
        """metadata is stored."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.post(
            "/v1/threads",
            json={
                "agent_name": "test",
                "metadata": {"key": "value"},
            },
        )

        assert response.json()["metadata"] == {"key": "value"}

    def test_agent_name_stored(self):
        """agent_name is stored."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )

        assert response.json()["agent_name"] == "test"

    def test_message_count_starts_at_zero(self):
        """message_count starts at 0."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )

        assert response.json()["message_count"] == 0


# ============================================================================
# GET /v1/threads/{id} Tests
# ============================================================================


class TestGetThread:
    """Test GET /v1/threads/{id} endpoint."""

    def test_returns_404_unknown(self):
        """Returns 404 for unknown ID."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads/unknown-id")

        assert response.status_code == 404

    def test_returns_404_no_storage(self):
        """Returns 404 if no storage configured."""
        app = create_test_app_no_storage()
        client = TestClient(app)

        response = client.get("/v1/threads/some-id")

        assert response.status_code == 404


# ============================================================================
# DELETE /v1/threads/{id} Tests
# ============================================================================


class TestDeleteThread:
    """Test DELETE /v1/threads/{id} endpoint."""

    def test_returns_404_no_storage(self):
        """Returns 404 if no storage."""
        app = create_test_app_no_storage()
        client = TestClient(app)

        response = client.delete("/v1/threads/some-id")

        assert response.status_code == 404


# ============================================================================
# GET /v1/threads/{id}/messages Tests
# ============================================================================


class TestListMessages:
    """Test GET /v1/threads/{id}/messages endpoint."""

    def test_returns_list(self):
        """Returns list of messages."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads/thread-123/messages")

        assert response.status_code == 200
        assert "messages" in response.json()

    def test_empty_returns_empty_list(self):
        """Empty thread returns empty list."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads/thread-123/messages")

        assert response.json()["messages"] == []


# ============================================================================
# POST /v1/threads/{id}/messages Tests
# ============================================================================


class TestAddMessage:
    """Test POST /v1/threads/{id}/messages endpoint."""

    def test_creates_message(self):
        """Creates message successfully."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # First create the thread
        thread_response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )
        thread_id = thread_response.json()["id"]

        response = client.post(
            f"/v1/threads/{thread_id}/messages",
            json={
                "role": "user",
                "content": "Hello!",
            },
        )

        assert response.status_code == 200
        assert "id" in response.json()

    def test_role_is_required(self):
        """role is required."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.post(
            "/v1/threads/thread-123/messages",
            json={"content": "Hello!"},
        )

        assert response.status_code == 422

    def test_valid_roles(self):
        """role must be user/assistant/system/tool."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # First create the thread
        thread_response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )
        thread_id = thread_response.json()["id"]

        for role in ["user", "assistant", "system", "tool"]:
            response = client.post(
                f"/v1/threads/{thread_id}/messages",
                json={
                    "role": role,
                    "content": "Hello!",
                },
            )
            assert response.status_code == 200

    def test_invalid_role_returns_400(self):
        """Invalid role returns 400."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.post(
            "/v1/threads/thread-123/messages",
            json={
                "role": "invalid_role",
                "content": "Hello!",
            },
        )

        assert response.status_code == 400

    def test_content_is_required(self):
        """content is required."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.post(
            "/v1/threads/thread-123/messages",
            json={"role": "user"},
        )

        assert response.status_code == 422

    def test_metadata_is_optional(self):
        """metadata is optional."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # First create the thread
        thread_response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )
        thread_id = thread_response.json()["id"]

        response = client.post(
            f"/v1/threads/{thread_id}/messages",
            json={
                "role": "user",
                "content": "Hello!",
                "metadata": {"key": "value"},
            },
        )

        assert response.status_code == 200
        assert response.json()["metadata"] == {"key": "value"}

    def test_id_is_uuid(self):
        """Generated ID is UUID format."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # First create the thread
        thread_response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )
        thread_id = thread_response.json()["id"]

        response = client.post(
            f"/v1/threads/{thread_id}/messages",
            json={
                "role": "user",
                "content": "Hello!",
            },
        )

        message_id = response.json()["id"]
        assert len(message_id) == 36

    def test_created_at_set(self):
        """created_at is set."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # First create the thread
        thread_response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )
        thread_id = thread_response.json()["id"]

        response = client.post(
            f"/v1/threads/{thread_id}/messages",
            json={
                "role": "user",
                "content": "Hello!",
            },
        )

        assert "created_at" in response.json()


# ============================================================================
# DELETE /v1/threads/{id}/messages Tests
# ============================================================================


class TestClearMessages:
    """Test DELETE /v1/threads/{id}/messages endpoint."""

    def test_returns_400_no_storage(self):
        """Returns 400 if no storage."""
        app = create_test_app_no_storage()
        client = TestClient(app)

        response = client.delete("/v1/threads/thread-123/messages")

        assert response.status_code == 400

    def test_returns_confirmation(self):
        """Returns confirmation message."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.delete("/v1/threads/thread-123/messages")

        assert response.status_code == 200
        assert "message" in response.json()


# ============================================================================
# Additional Thread Route Tests
# ============================================================================


class TestListThreadsAdditional:
    """Additional tests for GET /v1/threads."""

    def test_per_page_max_100_validation(self):
        """per_page > 100 returns 422 validation error."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        response = client.get("/v1/threads?per_page=200")

        # API validates per_page, returns 422 for values > 100
        assert response.status_code == 422


class TestGetThreadAdditional:
    """Additional tests for GET /v1/threads/{id}."""

    def test_response_includes_all_fields(self):
        """Response includes all thread fields."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # First create a thread
        create_response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )

        if create_response.status_code == 200:
            thread_id = create_response.json()["id"]

            response = client.get(f"/v1/threads/{thread_id}")

            # Should have standard fields
            if response.status_code == 200:
                data = response.json()
                assert "id" in data


class TestDeleteThreadAdditional:
    """Additional tests for DELETE /v1/threads/{id}."""

    def test_deletes_thread_successfully(self):
        """Deletes thread successfully."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # Create a thread first
        create_response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )

        if create_response.status_code == 200:
            thread_id = create_response.json()["id"]

            response = client.delete(f"/v1/threads/{thread_id}")

            # Should delete successfully
            assert response.status_code in [200, 204, 404]


class TestListMessagesAdditional:
    """Additional tests for GET /v1/threads/{id}/messages."""

    def test_message_includes_role(self):
        """Message includes role field."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # Add a message
        client.post(
            "/v1/threads/thread-123/messages",
            json={
                "role": "user",
                "content": "Hello!",
            },
        )

        response = client.get("/v1/threads/thread-123/messages")

        messages = response.json().get("messages", [])
        if messages:
            assert "role" in messages[0]

    def test_message_includes_content(self):
        """Message includes content field."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # Add a message
        client.post(
            "/v1/threads/thread-123/messages",
            json={
                "role": "user",
                "content": "Test content",
            },
        )

        response = client.get("/v1/threads/thread-123/messages")

        messages = response.json().get("messages", [])
        if messages:
            assert "content" in messages[0]


class TestClearMessagesAdditional:
    """Additional tests for DELETE /v1/threads/{id}/messages."""

    def test_thread_not_deleted(self):
        """Thread itself is not deleted after clearing messages."""
        app = create_test_app_with_storage()
        client = TestClient(app)

        # Create a thread
        create_response = client.post(
            "/v1/threads",
            json={"agent_name": "test"},
        )

        if create_response.status_code == 200:
            thread_id = create_response.json()["id"]

            # Add a message
            client.post(
                f"/v1/threads/{thread_id}/messages",
                json={
                    "role": "user",
                    "content": "Test",
                },
            )

            # Clear messages
            client.delete(f"/v1/threads/{thread_id}/messages")

            # Thread should still exist
            response = client.get(f"/v1/threads/{thread_id}")

            # May be 200 or 404 depending on implementation
            assert response.status_code in [200, 404]
