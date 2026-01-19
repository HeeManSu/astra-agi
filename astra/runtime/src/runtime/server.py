"""
AstraServer - Main server class for running agents.

Similar to Agno's AgentOS, this provides a FastAPI-based server
for running agents, teams, and handling chat requests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import FastAPI


if TYPE_CHECKING:
    from framework.agents import Agent
    from framework.team import Team


class AstraServer:
    """
    Astra Server for running AI agents.

    Example:
        ```python
        from runtime import AstraServer
        from my_agents import researcher, writer

        # Without auth (local dev)
        server = AstraServer(
            agents=[researcher, writer],
        )

        # With simple auth (security key)
        server = AstraServer(
            agents=[researcher, writer],
            enable_auth=True,
            security_key="my-secret-key",
        )

        app = server.get_app()
        # Run with: uvicorn main:app --reload
        ```
    """

    def __init__(
        self,
        agents: list[Agent] | None = None,
        teams: list[Team] | None = None,
        storage: Any | None = None,
        name: str = "Astra Server",
        description: str = "AI Agent Server",
        version: str = "0.1.0",
        # Auth
        enable_auth: bool = False,
        security_key: str | None = None,
        jwt_secret: str | None = None,
        # CORS
        cors_allowed_origins: list[str] | None = None,
    ):
        """
        Initialize AstraServer.

        Args:
            agents: List of agents to register
            teams: List of teams to register
            storage: Storage backend for agents/teams
            name: Server name
            description: Server description
            version: API version
            enable_auth: Enable authentication middleware
            security_key: Simple auth key (alternative to JWT)
            jwt_secret: Secret for JWT token verification
            cors_allowed_origins: Allowed CORS origins
        """
        self.agents = agents or []
        self.teams = teams or []
        self.storage = storage

        self.name = name
        self.description = description
        self.version = version
        self.enable_auth = enable_auth
        self.security_key = security_key
        self.jwt_secret = jwt_secret
        self.cors_allowed_origins = cors_allowed_origins or ["*"]

        # Initialize all components in global registries
        self._initialize_storage()
        self._initialize_agents()
        self._initialize_teams()

        self._app: FastAPI | None = None

    def _initialize_storage(self) -> None:
        """Initialize and register storage in the global registry."""
        from runtime.registry import storage_registry

        if self.storage:
            storage_registry.set_default(self.storage)

    def _initialize_agents(self) -> None:
        """Initialize and register all agents in the global registry."""
        from runtime.registry import agent_registry, storage_registry

        default_storage = storage_registry.get_default()

        for agent in self.agents:
            # Configure storage if server-level storage provided
            if default_storage and hasattr(agent, "storage"):
                agent.storage = default_storage

            # Register in global registry
            agent_registry.register(agent)

    def _initialize_teams(self) -> None:
        """Initialize and register all teams in the global registry."""
        from runtime.registry import storage_registry, team_registry

        default_storage = storage_registry.get_default()

        for team in self.teams:
            # Configure storage if server-level storage provided
            if default_storage and hasattr(team, "storage"):
                team.storage = default_storage

            # Register in global registry
            team_registry.register(team)

    def _configure_auth(self) -> None:
        """Configure auth settings in server_config based on constructor args."""
        from runtime.app.config import server_config

        # Override config with constructor values if provided
        if self.security_key:
            server_config.security_key = self.security_key
        if self.jwt_secret:
            server_config.jwt_secret = self.jwt_secret

    def get_app(self) -> FastAPI:
        """
        Get the FastAPI application.

        Returns:
            FastAPI application instance
        """
        if self._app is None:
            self._app = self._create_app()
        return self._app

    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI app."""
        from runtime.app.app import create_app

        app = create_app(
            title=self.name,
            description=self.description,
            version=self.version,
            cors_allowed_origins=self.cors_allowed_origins,
        )

        # Configure auth settings
        self._configure_auth()

        # Add auth middleware if enabled
        if self.enable_auth:
            self._add_auth_middleware(app)

        # Add routes
        self._add_routes(app)

        return app

    def _add_auth_middleware(self, app: FastAPI) -> None:
        """Add authentication middleware to the app."""
        from runtime.auth.middleware import AuthMiddleware

        app.add_middleware(AuthMiddleware)

    def _add_routes(self, app: FastAPI) -> None:
        """Add API routes to the app."""
        from runtime.routes import (
            agents_router,
            health_router,
            teams_router,
            threads_router,
        )

        app.include_router(health_router)
        app.include_router(agents_router)
        app.include_router(teams_router)
        app.include_router(threads_router)
