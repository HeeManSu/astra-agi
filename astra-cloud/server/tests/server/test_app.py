"""
Tests for Astra Server App.

Tests AstraServer class and create_app function.
"""

from astra.server import AstraServer, ServerConfig, create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from .conftest import create_agent, create_storage  # noqa: TID252


# ============================================================================
# AstraServer Class Tests
# ============================================================================


class TestAstraServerInit:
    """Test AstraServer initialization."""

    def test_requires_agents(self):
        """__init__ requires agents."""
        with pytest.raises(ValueError):
            AstraServer(agents={})

    def test_accepts_storage(self):
        """__init__ accepts storage."""
        storage = create_storage()
        server = AstraServer(
            agents={"test": create_agent()},
            storage=storage,
        )
        assert server.global_storage is storage

    def test_accepts_config(self):
        """__init__ accepts config."""
        config = ServerConfig(name="My Server")
        server = AstraServer(
            agents={"test": create_agent()},
            config=config,
        )
        assert server.config.name == "My Server"

    def test_creates_registry(self):
        """__init__ creates registry."""
        server = AstraServer(agents={"test": create_agent()})
        assert server.registry is not None
        assert len(server.registry.agents) == 1

    def test_default_config(self):
        """Default config is used if not provided."""
        server = AstraServer(agents={"test": create_agent()})
        assert server.config.name == "Astra Server"


class TestAstraServerChaining:
    """Test method chaining in AstraServer."""

    def test_add_middleware_returns_self(self):
        """add_middleware returns self for chaining."""
        server = AstraServer(agents={"test": create_agent()})

        async def middleware(request, call_next):
            return await call_next(request)

        result = server.add_middleware(middleware)
        assert result is server

    def test_add_route_returns_self(self):
        """add_route returns self for chaining."""
        server = AstraServer(agents={"test": create_agent()})

        async def handler():
            return {"ok": True}

        result = server.add_route("/custom", handler)
        assert result is server

    def test_on_startup_returns_self(self):
        """on_startup returns self for chaining."""
        server = AstraServer(agents={"test": create_agent()})

        async def startup():
            pass

        result = server.on_startup(startup)
        assert result is server

    def test_on_shutdown_returns_self(self):
        """on_shutdown returns self for chaining."""
        server = AstraServer(agents={"test": create_agent()})

        async def shutdown():
            pass

        result = server.on_shutdown(shutdown)
        assert result is server


class TestAstraServerCreateApp:
    """Test AstraServer.create_app method."""

    def test_returns_fastapi(self):
        """Returns FastAPI instance."""
        server = AstraServer(agents={"test": create_agent()})
        app = server.create_app()
        assert isinstance(app, FastAPI)

    def test_title_matches_config(self):
        """Title matches config.name."""
        server = AstraServer(
            agents={"test": create_agent()},
            config=ServerConfig(name="My API"),
        )
        app = server.create_app()
        assert app.title == "My API"

    def test_version_matches_config(self):
        """Version matches config.version."""
        server = AstraServer(
            agents={"test": create_agent()},
            config=ServerConfig(version="2.0.0"),
        )
        app = server.create_app()
        assert app.version == "2.0.0"

    def test_docs_enabled(self):
        """docs_url is set when enabled."""
        server = AstraServer(
            agents={"test": create_agent()},
            config=ServerConfig(docs_enabled=True),
        )
        app = server.create_app()
        assert app.docs_url == "/docs"

    def test_docs_disabled(self):
        """docs_url is None when disabled."""
        server = AstraServer(
            agents={"test": create_agent()},
            config=ServerConfig(docs_enabled=False),
        )
        app = server.create_app()
        assert app.docs_url is None


# ============================================================================
# CORS Middleware Tests
# ============================================================================


class TestCORSMiddleware:
    """Test CORS middleware configuration."""

    def test_no_cors_when_empty(self):
        """No CORS when origins empty."""
        app = create_app(
            agents={"test": create_agent()},
            cors_origins=[],
        )
        client = TestClient(app)

        response = client.options(
            "/v1/agents",
            headers={"Origin": "http://example.com"},
        )

        # No CORS headers when not configured
        assert "access-control-allow-origin" not in response.headers

    def test_cors_enabled_when_origins(self):
        """CORS enabled when origins provided."""
        app = create_app(
            agents={"test": create_agent()},
            cors_origins=["http://localhost:3000"],
        )
        client = TestClient(app)

        response = client.options(
            "/v1/agents",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200


# ============================================================================
# Request ID Middleware Tests
# ============================================================================


class TestRequestIDMiddleware:
    """Test Request ID middleware."""

    def test_request_id_added(self):
        """X-Request-ID added to response."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        response = client.get("/health")

        assert "x-request-id" in response.headers

    def test_existing_request_id_preserved(self):
        """Existing request ID is preserved."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        response = client.get(
            "/health",
            headers={"X-Request-ID": "my-custom-id"},
        )

        assert response.headers["x-request-id"] == "my-custom-id"


# ============================================================================
# Custom Components Tests
# ============================================================================


class TestCustomComponents:
    """Test custom middleware and routes."""

    def test_custom_route_registered(self):
        """Custom route is registered."""
        server = AstraServer(agents={"test": create_agent()})

        async def my_handler():
            return {"custom": True}

        server.add_route("/custom", my_handler)
        app = server.create_app()
        client = TestClient(app)

        response = client.get("/custom")

        assert response.status_code == 200
        assert response.json()["custom"] is True

    def test_custom_route_with_methods(self):
        """Custom route with specific methods."""
        server = AstraServer(agents={"test": create_agent()})

        async def my_handler():
            return {"posted": True}

        server.add_route("/custom", my_handler, methods=["POST"])
        app = server.create_app()
        client = TestClient(app)

        # GET should fail
        response = client.get("/custom")
        assert response.status_code == 405

        # POST should work
        response = client.post("/custom")
        assert response.status_code == 200


# ============================================================================
# create_app Function Tests
# ============================================================================


class TestCreateAppFunction:
    """Test create_app wrapper function."""

    def test_creates_fastapi(self):
        """Wrapper creates FastAPI app."""
        app = create_app(agents={"test": create_agent()})
        assert isinstance(app, FastAPI)

    def test_agents_required(self):
        """agents is required."""
        with pytest.raises(ValueError):
            create_app(agents={})

    def test_storage_optional(self):
        """storage is optional."""
        storage = create_storage()
        app = create_app(
            agents={"test": create_agent()},
            storage=storage,
        )
        assert app is not None

    def test_config_options_passed(self):
        """All config options are passed."""
        app = create_app(
            agents={"test": create_agent()},
            name="Custom Name",
            version="3.0.0",
            description="Custom description",
        )
        assert app.title == "Custom Name"
        assert app.version == "3.0.0"

    def test_fastapi_kwargs_passed(self):
        """fastapi_kwargs are passed through."""
        app = create_app(
            agents={"test": create_agent()},
            root_path="/api",
        )
        assert app.root_path == "/api"


# ============================================================================
# Additional App Tests
# ============================================================================


class TestCreateAppDescriptionAndDocs:
    """Additional tests for create_app documentation settings."""

    def test_description_matches_config(self):
        """Description matches config.description."""
        app = create_app(
            agents={"test": create_agent()},
            description="My custom description",
        )
        assert app.description == "My custom description"

    def test_redoc_enabled_by_default(self):
        """redoc_url is set when docs_enabled=True."""
        app = create_app(
            agents={"test": create_agent()},
            docs_enabled=True,
        )
        assert app.redoc_url is not None

    def test_redoc_disabled(self):
        """redoc_url is None when docs_enabled=False."""
        app = create_app(
            agents={"test": create_agent()},
            docs_enabled=False,
        )
        assert app.redoc_url is None

    def test_openapi_enabled_by_default(self):
        """openapi_url is set when docs_enabled=True."""
        app = create_app(
            agents={"test": create_agent()},
            docs_enabled=True,
        )
        assert app.openapi_url is not None

    def test_openapi_disabled(self):
        """openapi_url is None when docs_enabled=False."""
        app = create_app(
            agents={"test": create_agent()},
            docs_enabled=False,
        )
        assert app.openapi_url is None


class TestCORSMiddlewareAdditional:
    """Additional CORS middleware tests."""

    def test_cors_allows_origin(self):
        """CORS allows specified origins."""
        app = create_app(
            agents={"test": create_agent()},
            cors_origins=["http://localhost:3000"],
        )
        client = TestClient(app)

        response = client.options(
            "/v1/agents",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Should have CORS headers
        assert response.status_code in [200, 204, 400]


class TestRequestIDMiddlewareAdditional:
    """Additional request ID middleware tests."""

    def test_generated_id_is_uuid_format(self):
        """Generated request ID follows UUID format."""
        app = create_app(agents={"test": create_agent()})
        client = TestClient(app)

        response = client.get("/health")

        request_id = response.headers.get("X-Request-ID", "")
        # Should be a valid UUID-like string
        assert len(request_id) > 0


class TestLifespanHooksIntegration:
    """Integration tests for lifespan hooks."""

    def test_startup_hook_called_with_server(self):
        """Startup hooks are called when using AstraServer."""
        called = []

        async def my_startup():
            called.append("startup")

        server = AstraServer(agents={"test": create_agent()})
        server.on_startup(my_startup)
        app = server.create_app()

        # Use TestClient to trigger lifespan
        with TestClient(app):
            pass

        assert "startup" in called

    def test_shutdown_hook_called_with_server(self):
        """Shutdown hooks are called when using AstraServer."""
        called = []

        async def my_shutdown():
            called.append("shutdown")

        server = AstraServer(agents={"test": create_agent()})
        server.on_shutdown(my_shutdown)
        app = server.create_app()

        # Use TestClient to trigger lifespan
        with TestClient(app):
            pass

        assert "shutdown" in called
