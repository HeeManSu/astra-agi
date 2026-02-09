"""App lifespan management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import sys

from fastapi import FastAPI
from framework.tool.mcp.toolkit import MCPToolkit


# Track all connected MCP toolkits for cleanup
_connected_mcp_toolkits: list[MCPToolkit] = []


def _get_all_mcp_toolkits() -> list[MCPToolkit]:
    """Collect all MCP toolkits from registered agents and teams."""
    from runtime.registry import agent_registry, team_registry

    toolkits: list[MCPToolkit] = []
    seen_names: set[str] = set()

    # From agents
    for agent in agent_registry.list_all():
        for tool in agent.tools or []:
            if isinstance(tool, MCPToolkit) and tool.name not in seen_names:
                toolkits.append(tool)
                seen_names.add(tool.name)

    # From teams
    for team in team_registry.list_all():
        for member in team.members or []:
            agent = getattr(member, "agent", member)
            for tool in getattr(agent, "tools", []) or []:
                if isinstance(tool, MCPToolkit) and tool.name not in seen_names:
                    toolkits.append(tool)
                    seen_names.add(tool.name)

    return toolkits


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan.

    Startup order:
        1. Observability
        2. Storage
        3. MCP connections (long-lived)
        4. Tool sync (uses open MCP connections)

    Shutdown order:
        1. MCP connections
        2. Storage
        3. Observability
    """
    global _connected_mcp_toolkits

    from runtime.registry import storage_registry

    # --- Startup ---

    # 1. Initialize Observability
    telemetry_config = getattr(app.state, "telemetry_config", None)
    if telemetry_config and telemetry_config.enabled:
        try:
            from observability import ObservabilityEngine, init

            obs_storage = telemetry_config.db_path
            await obs_storage.init()

            obs_engine = ObservabilityEngine(obs_storage, debug_mode=telemetry_config.debug)
            app.state.observability = obs_engine
            init(obs_engine)

            sys.stdout.write(f"Observability initialized (db: {telemetry_config.db_path})\n")
        except ImportError:
            app.state.observability = None
        except Exception as e:
            app.state.observability = None
            sys.stdout.write(f"Observability init failed: {e}\n")
    else:
        app.state.observability = None

    # 2. Connect storage
    storage = storage_registry.get_default()
    if storage and hasattr(storage, "connect"):
        await storage.connect()

    # 3. Connect all MCP toolkits (long-lived, before tool sync)
    mcp_toolkits = _get_all_mcp_toolkits()
    for toolkit in mcp_toolkits:
        try:
            await toolkit.connect()
            _connected_mcp_toolkits.append(toolkit)
            sys.stdout.write(f"[MCP] Connected to '{toolkit.name}'\n")
        except Exception as e:  # noqa: PERF203
            sys.stdout.write(f"[MCP] Failed to connect to '{toolkit.name}': {e}\n")

    # 4. Sync tools to DB (uses already-open MCP connections)
    astra_server = getattr(app.state, "astra_server", None)
    if astra_server and hasattr(astra_server, "sync_tools"):
        report = await astra_server.sync_tools()
        sys.stdout.write(f"Tools synced: {report}\n")

    sys.stdout.write("Astra Server started\n")

    yield

    # --- Shutdown ---

    # 1. Disconnect MCP toolkits
    for toolkit in _connected_mcp_toolkits:
        try:
            await toolkit.close()
            sys.stdout.write(f"[MCP] Disconnected from '{toolkit.name}'\n")
        except Exception:  # noqa: PERF203
            pass
    _connected_mcp_toolkits.clear()

    # 2. Disconnect storage
    if storage and hasattr(storage, "disconnect"):
        await storage.disconnect()

    # 3. Shutdown observability
    obs = getattr(app.state, "observability", None)
    if obs:
        await obs.storage.close()

    sys.stdout.write("Astra Server stopped\n")
