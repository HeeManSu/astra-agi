"""
Astra Server Application.

Main entry point for creating FastAPI applications from Astra agents.
Provides both simple (create_app) and advanced (AstraServer) interfaces.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
import os
from pathlib import Path
import time
from typing import Any
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from astra.server.auth.routes import create_auth_router
from astra.server.config import ServerConfig
from astra.server.lifecycle import create_lifespan
from astra.server.registry import create_registry
from astra.server.routes import (
    create_agent_router,
    create_meta_router,
    create_playground_router,
    create_thread_router,
)


logger = logging.getLogger(__name__)


class AstraServer:
    """
    Advanced interface for creating Astra servers.

    Provides granular control over:
    - Middleware configuration
    - Custom routes
    - Lifecycle hooks
    - Server configuration

    Example:
        server = AstraServer(
            agents={"sales": sales_agent},
            config=ServerConfig(name="My Server"),
        )
        server.add_middleware(auth_middleware)
        server.add_route("/custom", custom_handler)
        app = server.create_app()
    """

    def __init__(
        self,
        agents: dict[str, Any],
        storage: Any | None = None,
        config: ServerConfig | None = None,
    ) -> None:
        """
        Initialize AstraServer.

        Args:
            agents: Dict of agent name -> Agent instance
            storage: Optional global storage fallback
            config: Optional ServerConfig (defaults will be used if not provided)

        Raises:
            ValueError: If no agents provided or validation fails
        """
        self.config = config or ServerConfig()
        self.global_storage = storage

        # Create registry (validates and discovers)
        self.registry = create_registry(
            agents=agents,
            global_storage=storage,
        )

        # Custom components
        self._middlewares: list[Callable] = []
        self._custom_routes: list[tuple[str, Callable, list[str]]] = []
        self._startup_hooks: list[Callable] = []
        self._shutdown_hooks: list[Callable] = []

        # Track start time for uptime
        self._start_time: float = 0

    def add_middleware(self, middleware_fn: Callable) -> AstraServer:
        """
        Add custom middleware.

        Args:
            middleware_fn: Middleware function

        Returns:
            Self for chaining
        """
        self._middlewares.append(middleware_fn)
        return self

    def add_route(
        self,
        path: str,
        handler: Callable,
        methods: list[str] | None = None,
    ) -> AstraServer:
        """
        Add custom route.

        Args:
            path: Route path (e.g., "/custom")
            handler: Route handler function
            methods: HTTP methods (default: ["GET"])

        Returns:
            Self for chaining
        """
        self._custom_routes.append((path, handler, methods or ["GET"]))
        return self

    def on_startup(self, hook: Callable) -> AstraServer:
        """
        Add startup hook.

        Args:
            hook: Async function to run on startup

        Returns:
            Self for chaining
        """
        self._startup_hooks.append(hook)
        return self

    def on_shutdown(self, hook: Callable) -> AstraServer:
        """
        Add shutdown hook.

        Args:
            hook: Async function to run on shutdown

        Returns:
            Self for chaining
        """
        self._shutdown_hooks.append(hook)
        return self

    def create_app(self, **fastapi_kwargs: Any) -> FastAPI:
        """
        Create FastAPI application.

        Args:
            **fastapi_kwargs: Additional kwargs to pass to FastAPI

        Returns:
            Configured FastAPI application
        """
        self._start_time = time.time()

        # Combine all startup hooks
        async def combined_startup():
            for hook in self._startup_hooks:
                result = hook()
                if hasattr(result, "__await__"):
                    await result

        # Combine all shutdown hooks
        async def combined_shutdown():
            for hook in self._shutdown_hooks:
                result = hook()
                if hasattr(result, "__await__"):
                    await result

        # Create lifespan
        lifespan = create_lifespan(
            registry=self.registry,
            custom_startup=combined_startup if self._startup_hooks else None,
            custom_shutdown=combined_shutdown if self._shutdown_hooks else None,
        )

        # Create FastAPI app
        app = FastAPI(
            title=self.config.name,
            version=self.config.version,
            description=self.config.description,
            docs_url="/docs" if self.config.docs_enabled else None,
            redoc_url="/redoc" if self.config.docs_enabled else None,
            openapi_url="/openapi.json" if self.config.docs_enabled else None,
            lifespan=lifespan,
            **fastapi_kwargs,
        )

        # Add CORS middleware
        if self.config.cors_origins:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.cors_origins,
                allow_credentials=self.config.cors_allow_credentials,
                allow_methods=self.config.cors_allow_methods,
                allow_headers=self.config.cors_allow_headers,
            )

        # Add request ID middleware
        @app.middleware("http")
        async def request_id_middleware(request: Request, call_next: Callable) -> Response:
            request_id = request.headers.get(
                self.config.request_id_header,
                str(uuid.uuid4())[:8],
            )
            request.state.request_id = request_id

            response = await call_next(request)
            response.headers[self.config.request_id_header] = request_id
            return response

        # Add request logging middleware
        if self.config.log_requests:

            @app.middleware("http")
            async def logging_middleware(request: Request, call_next: Callable) -> Response:
                start = time.time()
                response = await call_next(request)
                duration = time.time() - start

                request_id = getattr(request.state, "request_id", "unknown")
                logger.info(
                    f"[{request_id}] {request.method} {request.url.path} "
                    f"- {response.status_code} ({duration:.3f}s)"
                )

                return response

        # Add custom middlewares
        for middleware_fn in self._middlewares:
            app.middleware("http")(middleware_fn)

        # Add built-in routes
        app.include_router(
            create_meta_router(
                registry=self.registry,
                config=self.config,
                start_time=self._start_time,
            )
        )
        app.include_router(create_agent_router(registry=self.registry))
        app.include_router(create_thread_router(registry=self.registry))
        app.include_router(create_playground_router(registry=self.registry))
        app.include_router(create_auth_router(registry=self.registry, config=self.config))

        # Store config in app state for middleware access
        app.state.config = self.config

        # Add custom routes
        for path, handler, methods in self._custom_routes:
            app.add_api_route(path, handler, methods=methods)

        # Serve Playground UI if available
        if self.config.playground_enabled:
            self._setup_playground(app)

        logger.info(f"Created FastAPI app: {self.config.name} v{self.config.version}")

        return app

    def _setup_playground(self, app: FastAPI) -> None:
        """Set up playground static file serving."""
        # Look for playground dist in multiple locations
        possible_paths = [
            Path(__file__).parent / "playground-dist",  # In package
            Path(__file__).parent.parent.parent.parent.parent / "playground" / "dist",  # Dev mode
        ]

        playground_dir = None
        for path in possible_paths:
            if path.exists() and (path / "index.html").exists():
                playground_dir = path
                break

        if not playground_dir:
            logger.warning(
                "Playground UI not found. Run 'npm run build' in packages/playground to enable."
            )
            return

        logger.info(f"Serving playground from: {playground_dir}")

        # Serve static assets
        assets_dir = playground_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="playground-assets")

        # Serve index.html for all non-API routes
        @app.get("/", response_class=HTMLResponse, response_model=None)
        @app.get("/{path:path}", response_class=HTMLResponse, response_model=None)
        async def serve_playground(path: str = ""):
            # Skip API routes and docs
            if path.startswith(("api/", "docs", "redoc", "openapi.json")):
                return None

            index_path = playground_dir / "index.html"  # type: ignore[operator]
            if not index_path.exists():
                return None

            content = index_path.read_text(encoding="utf-8")

            # Inject server configuration
            host = os.getenv("HOST", "localhost")
            port = os.getenv("PORT", str(self.config.port))
            protocol = "https" if os.getenv("HTTPS") else "http"

            content = content.replace("%%ASTRA_SERVER_HOST%%", host)
            content = content.replace("%%ASTRA_SERVER_PORT%%", port)
            content = content.replace("%%ASTRA_SERVER_PROTOCOL%%", protocol)

            return HTMLResponse(content=content)


def create_app(
    agents: dict[str, Any],
    *,
    storage: Any | None = None,
    name: str = "Astra Server",
    version: str = "1.0.0",
    description: str = "AI Agent Server powered by Astra",
    docs_enabled: bool = True,
    cors_origins: list[str] | None = None,
    debug: bool = False,
    **fastapi_kwargs: Any,
) -> FastAPI:
    """
    Create a FastAPI application from Astra agents.

    This is the simple, functional interface. For more control,
    use the AstraServer class.

    Args:
        agents: Dict of agent name -> Agent instance
        storage: Optional global storage fallback
        name: Server name for documentation
        version: API version
        description: Server description
        docs_enabled: Enable OpenAPI documentation
        cors_origins: List of allowed CORS origins
        debug: Enable debug mode
        **fastapi_kwargs: Additional kwargs for FastAPI

    Returns:
        FastAPI application ready to run

    Raises:
        ValueError: If no agents provided or validation fails

    Example:
        from astra import Agent, Gemini
        from astra.server import create_app

        agent = Agent(
            name="assistant",
            model=Gemini(model="gemini-2.0-flash"),
            instructions="You are a helpful assistant.",
        )

        app = create_app(
            agents={"assistant": agent},
            cors_origins=["*"],
        )

        # Run with: uvicorn main:app
    """
    config = ServerConfig(
        name=name,
        version=version,
        description=description,
        docs_enabled=docs_enabled,
        cors_origins=cors_origins or [],
        debug=debug,
    )

    server = AstraServer(
        agents=agents,
        storage=storage,
        config=config,
    )

    return server.create_app(**fastapi_kwargs)
