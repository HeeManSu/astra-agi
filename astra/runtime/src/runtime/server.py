"""
AstraServer - Main server class for running agents.

Provides a FastAPI-based server for running agents, teams, and handling chat requests.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from framework.tool.mcp import MCPToolkit

from runtime.sync.tool_sync import sync_local_tools, sync_mcp_tools


if TYPE_CHECKING:
    from framework.agents import Agent
    from framework.team import Team


@dataclass
class TelemetryConfig:
    """
    Configuration for observability/telemetry.

    Attributes:
        enabled: Whether telemetry is enabled
        db_path: Path to SQLite database or a StorageBackend instance
        debug: Enable debug-level logging
    """

    enabled: bool = True
    db_path: Any = "./observability.db"
    debug: bool = False


class AstraServer:
    """
    Astra Server for running AI agents.

    Example:
        ```python
        from runtime import AstraServer, TelemetryConfig
        from my_agents import researcher, writer

        server = AstraServer(
            agents=[researcher, writer],
            telemetry=TelemetryConfig(
                enabled=True,
                db_path="./my_obs.db",
                debug=True,
            ),
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
        auth_enabled: bool = True,
        # CORS
        cors_allowed_origins: list[str] | None = None,
        # Telemetry
        telemetry: TelemetryConfig | None = None,
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
            auth_enabled: Enable JWT authentication (requires ASTRA_JWT_SECRET env var)
            cors_allowed_origins: Allowed CORS origins
            telemetry: Telemetry/observability configuration
        """
        self.agents = agents or []
        self.teams = teams or []
        self.storage = storage

        self.name = name
        self.description = description
        self.version = version
        self._auth_enabled = auth_enabled
        self.cors_allowed_origins = cors_allowed_origins or ["*"]
        self.telemetry = telemetry or TelemetryConfig()

        # Initialize all components in global registries
        self._initialize_storage()
        self._initialize_agents()
        self._initialize_teams()

        self._app: FastAPI | None = None

    @property
    def auth_enabled(self) -> bool:
        """Check if auth is enabled (flag + ASTRA_JWT_SECRET set)."""
        return self._auth_enabled and bool(os.getenv("ASTRA_JWT_SECRET"))

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
            if default_storage and hasattr(agent, "storage"):
                agent.storage = default_storage
            agent_registry.register(agent)

    def _initialize_teams(self) -> None:
        """Initialize and register all teams in the global registry."""
        from runtime.registry import storage_registry, team_registry

        default_storage = storage_registry.get_default()

        for team in self.teams:
            if default_storage and hasattr(team, "storage"):
                team.storage = default_storage
            team_registry.register(team)

    async def sync_tools(self) -> dict[str, Any]:
        """Sync tools from agents to database. Returns sync report."""
        from framework.storage.client import StorageClient
        from framework.tool import Tool

        from runtime.registry import storage_registry
        from runtime.sync.tool_sync import SyncReport

        report = SyncReport()

        storage = storage_registry.get_default()
        if storage is None or not isinstance(storage, StorageClient):
            return report.to_dict()

        for agent in self.agents:
            tools = getattr(agent, "tools", []) or []
            local_tools = [t for t in tools if isinstance(t, Tool)]
            mcp_tools = [t for t in tools if isinstance(t, MCPToolkit)]

            if local_tools:
                synced, unchanged = await sync_local_tools(storage, local_tools, source="local")
                report.local_synced += synced
                report.local_unchanged += unchanged

            if mcp_tools:
                mcp_results = await sync_mcp_tools(storage, mcp_tools, source="mcp")
                for server, (synced, unchanged) in mcp_results.items():
                    report.mcp_synced[server] = report.mcp_synced.get(server, 0) + synced
                    report.mcp_unchanged[server] = report.mcp_unchanged.get(server, 0) + unchanged

        return report.to_dict()

    def get_app(self) -> FastAPI:
        """Get the FastAPI application."""
        if self._app is None:
            self._app = self._create_app()
        return self._app

    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI app."""
        from fastapi.middleware.cors import CORSMiddleware

        from runtime.app.app import create_app

        # Create app with telemetry config (stored in app.state before lifespan)
        app = create_app(
            title=self.name,
            description=self.description,
            version=self.version,
            cors_allowed_origins=None,  # Don't add CORS here
            telemetry_config=self.telemetry,
        )

        # Store server reference for lifespan access (initialize_tools)
        app.state.astra_server = self

        # Add auth middleware if enabled (added first, processed second)
        if self.auth_enabled:
            self._add_auth_middleware(app)

        # Add CORS middleware LAST (processed FIRST in request chain)
        # This ensures CORS headers are added even for preflight requests
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

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
            auth_router,
            health_router,
            observability_router,
            teams_router,
            threads_router,
            tools_router,
        )

        app.include_router(health_router)
        app.include_router(auth_router)
        app.include_router(agents_router)
        app.include_router(teams_router)
        app.include_router(threads_router)
        app.include_router(tools_router)
        app.include_router(observability_router)
