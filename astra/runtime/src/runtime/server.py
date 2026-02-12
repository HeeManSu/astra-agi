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
    from observability.storage.base import StorageBackend


@dataclass
class TelemetryConfig:
    """
    Configuration for observability/telemetry.

    Attributes:
        enabled: Whether telemetry is enabled
        db_path: Path to SQLite database file or observability StorageBackend instance
        debug: Enable debug-level logging
    """

    enabled: bool = True
    db_path: str | StorageBackend = "./observability.db"
    debug: bool = False


@dataclass
class StartupSyncConfig:
    """
    Configuration for startup MCP connect and tool sync behavior.

    Attributes:
        require_mcp_sync: If True, startup fails when any MCP tool sync fails
        mcp_connect_timeout_seconds: Timeout for initial MCP connect
        mcp_connect_concurrency: Max MCP servers to connect in parallel during startup
        mcp_list_timeout_seconds: Timeout for MCP tool discovery during sync
        mcp_retries: Retry attempts for MCP connect/list operations
        mcp_retry_backoff_seconds: Base backoff delay between retries
    """

    require_mcp_sync: bool = True
    mcp_connect_timeout_seconds: float = 10.0
    mcp_connect_concurrency: int = 10
    mcp_list_timeout_seconds: float = 10.0
    mcp_retries: int = 2
    mcp_retry_backoff_seconds: float = 0.5


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
        storage: Any,
        agents: list[Agent] | None = None,
        teams: list[Team] | None = None,
        name: str = "Astra Server",
        description: str = "AI Agent Server",
        version: str = "0.1.0",
        # Auth
        auth_enabled: bool = True,
        # CORS
        cors_allowed_origins: list[str] | None = None,
        # Telemetry
        telemetry: TelemetryConfig | None = None,
        # Startup sync behavior
        startup_sync: StartupSyncConfig | None = None,
    ):
        """
        Initialize AstraServer.

        Args:
            storage: Storage backend for agents/teams (required, must be StorageClient instance)
            agents: List of agents to register
            teams: List of teams to register
            name: Server name
            description: Server description
            version: API version
            auth_enabled: Enable JWT authentication (requires ASTRA_JWT_SECRET env var)
            cors_allowed_origins: Allowed CORS origins
            telemetry: Telemetry/observability configuration
            startup_sync: Startup sync behavior configuration
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
        self.startup_sync = startup_sync or StartupSyncConfig()

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
        """Initialize and validate storage in the global registry."""
        from framework.storage.client import StorageClient

        from runtime.registry import storage_registry

        # Validate storage is a StorageClient
        if not isinstance(self.storage, StorageClient):
            raise RuntimeError(
                "Invalid storage backend. Expected StorageClient instance. "
                "Example: storage=StorageClient(storage=MongoDBStorage(...))"
            )

        # Set as global default in registry
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

    async def sync_tools(
        self,
        *,
        mcp_list_timeout_seconds: float = 10.0,
        mcp_retries: int = 2,
        mcp_retry_backoff_seconds: float = 0.5,
    ) -> dict[str, Any]:
        """Sync tools from agents to database. Returns sync report."""
        from framework.storage.client import StorageClient
        from framework.tool import Tool

        from runtime.registry import storage_registry
        from runtime.sync.tool_sync import SyncReport

        report = SyncReport()

        storage = storage_registry.get_default()
        if not isinstance(storage, StorageClient):
            raise RuntimeError("Invalid storage backend configured. Expected StorageClient.")

        agents_to_sync: list[Any] = []
        seen_agents: dict[str, int] = {}

        def register_agent(agent: Any) -> None:
            """
            Deduplicate and validate agents before syncing.

            Problem solved:
            - Agents can appear multiple times (e.g., in both self.agents and as team members)
            - Prevents duplicate agent IDs across different agent objects
            - Ensures each agent has a valid ID before tool sync
            - Uses object identity (id()) to allow same agent instance to be safely shared
            """
            if agent is None:
                return
            raw_agent_id = getattr(agent, "id", None)
            if not isinstance(raw_agent_id, str) or not raw_agent_id.strip():
                raise RuntimeError(
                    "Agent ID is required for startup sync. Ensure each agent has a valid id."
                )
            agent_key = raw_agent_id.strip()
            existing_obj_id = seen_agents.get(agent_key)
            if existing_obj_id is not None:
                if existing_obj_id != id(agent):
                    raise RuntimeError(
                        f"Duplicate agent id '{agent_key}' detected for multiple agents. IDs must be unique."
                    )
                return
            seen_agents[agent_key] = id(agent)
            agents_to_sync.append(agent)

        # Include top-level agents
        for agent in self.agents:
            register_agent(agent)

        # Include all team members (including nested team members via flat_members)
        for team in self.teams:
            for member in getattr(team, "flat_members", []) or []:
                register_agent(getattr(member, "agent", None))

        all_local_tools: list[Tool] = []
        seen_local_tools: dict[str, int] = {}
        mcp_toolkits: list[MCPToolkit] = []
        seen_mcp_slugs: dict[str, int] = {}

        for agent in agents_to_sync:
            tools = getattr(agent, "tools", []) or []
            for tool in tools:
                if isinstance(tool, Tool):
                    raw_tool_slug = getattr(tool, "slug", None)
                    if not isinstance(raw_tool_slug, str) or not raw_tool_slug.strip():
                        raise RuntimeError(
                            "Tool slug is required for startup sync. Ensure each local tool has a valid slug."
                        )
                    key = raw_tool_slug.strip()
                    existing_obj_id = seen_local_tools.get(key)
                    if existing_obj_id is not None:
                        if existing_obj_id != id(tool):
                            raise RuntimeError(
                                f"Duplicate local tool slug '{key}' detected. Tool slugs must be unique."
                            )
                        continue
                    seen_local_tools[key] = id(tool)
                    all_local_tools.append(tool)
                elif isinstance(tool, MCPToolkit):
                    raw_mcp_slug = getattr(tool, "slug", None)
                    if not isinstance(raw_mcp_slug, str) or not raw_mcp_slug.strip():
                        raise RuntimeError(
                            "MCP toolkit slug is required for startup sync. Ensure each MCP toolkit has a valid slug."
                        )
                    key = raw_mcp_slug.strip()
                    existing_obj_id = seen_mcp_slugs.get(key)
                    if existing_obj_id is not None:
                        if existing_obj_id != id(tool):
                            raise RuntimeError(
                                f"Duplicate MCP toolkit slug '{key}' detected. MCP slugs must be unique."
                            )
                        continue
                    seen_mcp_slugs[key] = id(tool)
                    mcp_toolkits.append(tool)

        if all_local_tools:
            synced, unchanged = await sync_local_tools(storage, all_local_tools, source="local")
            report.local_synced += synced
            report.local_unchanged += unchanged

        if mcp_toolkits:
            mcp_results = await sync_mcp_tools(
                storage,
                mcp_toolkits,
                source="mcp",
                list_timeout_seconds=mcp_list_timeout_seconds,
                retries=mcp_retries,
                retry_backoff_seconds=mcp_retry_backoff_seconds,
            )
            for result in mcp_results:
                report.mcp_synced[result.server] = (
                    report.mcp_synced.get(result.server, 0) + result.synced
                )
                report.mcp_unchanged[result.server] = (
                    report.mcp_unchanged.get(result.server, 0) + result.unchanged
                )
                if result.error:
                    report.mcp_failed[result.server] = result.error

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
        app.state.startup_sync_config = self.startup_sync

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
