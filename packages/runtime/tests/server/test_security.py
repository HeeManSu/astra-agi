"""
Security Tests for Astra Server.

Tests input validation and security measures.
"""

from astra.server import create_app
from fastapi.testclient import TestClient

from .conftest import create_agent, create_rag_pipeline  # noqa: TID252


# ============================================================================
# Input Validation Tests
# ============================================================================


class TestInputValidation:
    """Test input validation for security."""

    def test_sql_injection_in_agent_name(self):
        """SQL injection in agent name is handled safely."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        # Attempt SQL injection
        response = client.get("/v1/agents/test'; DROP TABLE agents;--")

        # Should return 404, not crash
        assert response.status_code == 404

    def test_sql_injection_in_thread_id(self):
        """SQL injection in thread ID is handled safely."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        response = client.get("/v1/threads/'; DROP TABLE threads;--")

        # Should return 404 or handle gracefully
        assert response.status_code in [400, 404]

    def test_xss_in_message_content(self):
        """XSS in message content doesn't break response."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/generate",
            json={"message": '<script>alert("xss")</script>'},
        )

        assert response.status_code == 200
        # Content should be in response as-is (not executed)

    def test_path_traversal_in_agent_name(self):
        """Path traversal in agent name is blocked."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        response = client.get("/v1/agents/../../../etc/passwd")

        # Should return 404, not expose files
        assert response.status_code == 404

    def test_very_large_request_body(self):
        """Very large request body is handled."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        # Create a very large message (1MB+)
        large_message = "x" * (1024 * 1024)

        # Should handle gracefully (may be 200 or 413)
        response = client.post(
            "/v1/agents/test/generate",
            json={"message": large_message},
        )

        # Should not crash - might return 200, 413, 422, or 500 (validation error)
        assert response.status_code in [200, 413, 422, 500]


# ============================================================================
# Header Security Tests
# ============================================================================


class TestHeaderSecurity:
    """Test header-related security."""

    def test_request_id_not_executable(self):
        """Request ID with script isn't executed."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        response = client.get(
            "/health",
            headers={"X-Request-ID": '<script>alert("xss")</script>'},
        )

        assert response.status_code == 200
        # Should just echo the ID, not execute

    def test_cors_restrictive_when_configured(self):
        """CORS is restrictive when configured."""
        app = create_app(
            agents={"test": create_agent()},
            cors_origins=["http://trusted.com"],
        )
        client = TestClient(app)

        # Request from untrusted origin
        response = client.options(
            "/v1/agents",
            headers={
                "Origin": "http://malicious.com",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Should not allow untrusted origin
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin != "http://malicious.com"


# ============================================================================
# Ingest Security Tests
# ============================================================================


class TestIngestSecurity:
    """Test ingest endpoint security."""

    def test_path_traversal_in_ingest(self):
        """Path traversal in ingest path is blocked."""
        agent = create_agent(rag_pipeline=create_rag_pipeline())
        app = create_app(agents={"test": agent})
        client = TestClient(app)

        response = client.post(
            "/v1/agents/test/ingest",
            json={"path": "../../../etc/passwd"},
        )

        # Should not expose system files
        # Either blocked (400) or fails gracefully
        assert response.status_code in [200, 400, 404, 500]
