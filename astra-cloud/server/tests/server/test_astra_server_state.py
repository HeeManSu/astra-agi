"""
Tests for AstraServer Internal State.

Tests constructor state and method behavior.
"""

from astra.server import AstraServer, ServerConfig

from .conftest import create_agent, create_storage  # noqa: TID252


# ============================================================================
# Constructor State Tests
# ============================================================================


class TestConstructorState:
    """Test AstraServer constructor initializes state correctly."""

    def test_config_set_from_parameter(self):
        """self.config is set from parameter."""
        config = ServerConfig(name="Test Server")
        server = AstraServer(
            agents={"test": create_agent()},
            config=config,
        )
        assert server.config is config

    def test_config_defaults_when_not_provided(self):
        """self.config defaults when not provided."""
        server = AstraServer(agents={"test": create_agent()})
        assert server.config is not None
        assert isinstance(server.config, ServerConfig)

    def test_global_storage_set(self):
        """self.global_storage is set."""
        storage = create_storage()
        server = AstraServer(
            agents={"test": create_agent()},
            storage=storage,
        )
        assert server.global_storage is storage

    def test_registry_created(self):
        """self.registry is created correctly."""
        server = AstraServer(agents={"test": create_agent()})
        assert server.registry is not None
        assert "test" in server.registry.agents

    def test_middlewares_starts_empty(self):
        """self._middlewares starts empty."""
        server = AstraServer(agents={"test": create_agent()})
        assert server._middlewares == []

    def test_custom_routes_starts_empty(self):
        """self._custom_routes starts empty."""
        server = AstraServer(agents={"test": create_agent()})
        assert server._custom_routes == []

    def test_startup_hooks_starts_empty(self):
        """self._startup_hooks starts empty."""
        server = AstraServer(agents={"test": create_agent()})
        assert server._startup_hooks == []

    def test_shutdown_hooks_starts_empty(self):
        """self._shutdown_hooks starts empty."""
        server = AstraServer(agents={"test": create_agent()})
        assert server._shutdown_hooks == []

    def test_start_time_is_zero(self):
        """self._start_time is 0 initially."""
        server = AstraServer(agents={"test": create_agent()})
        assert server._start_time == 0


# ============================================================================
# add_middleware Tests
# ============================================================================


class TestAddMiddleware:
    """Test add_middleware method."""

    def test_adds_to_list(self):
        """Adds to self._middlewares list."""
        server = AstraServer(agents={"test": create_agent()})

        async def my_middleware(request, call_next):
            return await call_next(request)

        server.add_middleware(my_middleware)
        assert my_middleware in server._middlewares

    def test_multiple_calls_accumulate(self):
        """Multiple calls accumulate."""
        server = AstraServer(agents={"test": create_agent()})

        async def m1(request, call_next):
            return await call_next(request)

        async def m2(request, call_next):
            return await call_next(request)

        server.add_middleware(m1)
        server.add_middleware(m2)
        assert len(server._middlewares) == 2

    def test_returns_self(self):
        """Returns self for chaining."""
        server = AstraServer(agents={"test": create_agent()})

        async def m(request, call_next):
            return await call_next(request)

        result = server.add_middleware(m)
        assert result is server

    def test_order_preserved(self):
        """Order is preserved."""
        server = AstraServer(agents={"test": create_agent()})

        async def m1(request, call_next):
            return await call_next(request)

        async def m2(request, call_next):
            return await call_next(request)

        server.add_middleware(m1)
        server.add_middleware(m2)
        assert server._middlewares[0] is m1
        assert server._middlewares[1] is m2


# ============================================================================
# add_route Tests
# ============================================================================


class TestAddRoute:
    """Test add_route method."""

    def test_adds_to_list(self):
        """Adds to self._custom_routes list."""
        server = AstraServer(agents={"test": create_agent()})

        async def handler():
            return {}

        server.add_route("/custom", handler)
        assert len(server._custom_routes) == 1

    def test_stores_tuple(self):
        """Stores (path, handler, methods) tuple."""
        server = AstraServer(agents={"test": create_agent()})

        async def handler():
            return {}

        server.add_route("/custom", handler, methods=["POST"])
        route = server._custom_routes[0]
        assert route[0] == "/custom"
        assert route[1] is handler
        assert route[2] == ["POST"]

    def test_default_methods_is_get(self):
        """Default methods is ["GET"]."""
        server = AstraServer(agents={"test": create_agent()})

        async def handler():
            return {}

        server.add_route("/custom", handler)
        route = server._custom_routes[0]
        assert route[2] == ["GET"]

    def test_custom_methods(self):
        """Custom methods are stored."""
        server = AstraServer(agents={"test": create_agent()})

        async def handler():
            return {}

        server.add_route("/custom", handler, methods=["POST", "PUT"])
        route = server._custom_routes[0]
        assert route[2] == ["POST", "PUT"]

    def test_returns_self(self):
        """Returns self for chaining."""
        server = AstraServer(agents={"test": create_agent()})

        async def handler():
            return {}

        result = server.add_route("/custom", handler)
        assert result is server

    def test_multiple_calls_accumulate(self):
        """Multiple calls accumulate."""
        server = AstraServer(agents={"test": create_agent()})

        async def h1():
            return {}

        async def h2():
            return {}

        server.add_route("/r1", h1)
        server.add_route("/r2", h2)
        assert len(server._custom_routes) == 2


# ============================================================================
# on_startup Tests
# ============================================================================


class TestOnStartup:
    """Test on_startup method."""

    def test_adds_to_hooks(self):
        """Adds to self._startup_hooks."""
        server = AstraServer(agents={"test": create_agent()})

        async def hook():
            pass

        server.on_startup(hook)
        assert hook in server._startup_hooks

    def test_multiple_accumulate(self):
        """Multiple hooks accumulate."""
        server = AstraServer(agents={"test": create_agent()})

        async def h1():
            pass

        async def h2():
            pass

        server.on_startup(h1)
        server.on_startup(h2)
        assert len(server._startup_hooks) == 2

    def test_order_preserved(self):
        """Order is preserved."""
        server = AstraServer(agents={"test": create_agent()})

        async def h1():
            pass

        async def h2():
            pass

        server.on_startup(h1)
        server.on_startup(h2)
        assert server._startup_hooks[0] is h1
        assert server._startup_hooks[1] is h2

    def test_returns_self(self):
        """Returns self for chaining."""
        server = AstraServer(agents={"test": create_agent()})

        async def hook():
            pass

        result = server.on_startup(hook)
        assert result is server


# ============================================================================
# on_shutdown Tests
# ============================================================================


class TestOnShutdown:
    """Test on_shutdown method."""

    def test_adds_to_hooks(self):
        """Adds to self._shutdown_hooks."""
        server = AstraServer(agents={"test": create_agent()})

        async def hook():
            pass

        server.on_shutdown(hook)
        assert hook in server._shutdown_hooks

    def test_multiple_accumulate(self):
        """Multiple hooks accumulate."""
        server = AstraServer(agents={"test": create_agent()})

        async def h1():
            pass

        async def h2():
            pass

        server.on_shutdown(h1)
        server.on_shutdown(h2)
        assert len(server._shutdown_hooks) == 2

    def test_order_preserved(self):
        """Order is preserved."""
        server = AstraServer(agents={"test": create_agent()})

        async def h1():
            pass

        async def h2():
            pass

        server.on_shutdown(h1)
        server.on_shutdown(h2)
        assert server._shutdown_hooks[0] is h1
        assert server._shutdown_hooks[1] is h2

    def test_returns_self(self):
        """Returns self for chaining."""
        server = AstraServer(agents={"test": create_agent()})

        async def hook():
            pass

        result = server.on_shutdown(hook)
        assert result is server


# ============================================================================
# create_app Execution Tests
# ============================================================================


class TestCreateAppExecution:
    """Test create_app execution behavior."""

    def test_sets_start_time(self):
        """Sets self._start_time to current time."""
        server = AstraServer(agents={"test": create_agent()})
        assert server._start_time == 0

        server.create_app()

        assert server._start_time > 0

    def test_includes_agent_router(self):
        """Includes agent router."""
        server = AstraServer(agents={"test": create_agent()})
        app = server.create_app()

        # Check route exists (use getattr for BaseRoute compatibility)
        routes = [getattr(r, "path", None) for r in app.routes]
        assert "/v1/agents" in routes

    def test_includes_thread_router(self):
        """Includes thread router."""
        server = AstraServer(agents={"test": create_agent()})
        app = server.create_app()

        routes = [getattr(r, "path", None) for r in app.routes]
        assert "/v1/threads" in routes

    def test_includes_meta_router(self):
        """Includes meta router."""
        server = AstraServer(agents={"test": create_agent()})
        app = server.create_app()

        routes = [getattr(r, "path", None) for r in app.routes]
        assert "/health" in routes
        assert "/v1/meta" in routes
