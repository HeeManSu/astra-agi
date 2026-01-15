"""
Astra Server Lifecycle Management.

Handles startup and shutdown with fail-loud philosophy.
"""

from collections.abc import Callable
from contextlib import asynccontextmanager
import logging
import time
from typing import Any

from astra.server.registry import AgentRegistry


logger = logging.getLogger(__name__)


class LifecycleError(Exception):
    """Base exception for lifecycle errors."""


class StorageConnectionError(LifecycleError):
    """Failed to connect to storage backend."""


class MCPConnectionError(LifecycleError):
    """Failed to connect to MCP tool."""


def create_lifespan(
    registry: AgentRegistry,
    custom_startup: Callable[[], Any] | None = None,
    custom_shutdown: Callable[[], Any] | None = None,
):
    """
    Create FastAPI lifespan context manager.

    Handles:
    - Storage initialization (connect + create tables)
    - MCP tool connection/disconnection
    - Custom startup/shutdown hooks

    Args:
        registry: AgentRegistry with discovered resources
        custom_startup: Optional async function to run on startup
        custom_shutdown: Optional async function to run on shutdown

    Returns:
        Async context manager for FastAPI lifespan
    """

    @asynccontextmanager
    async def lifespan(app: Any):
        start_time = time.time()

        # ═══════════════════════════════════════════════════════════════
        # STARTUP
        # ═══════════════════════════════════════════════════════════════
        logger.info("=" * 60)
        logger.info("Starting Astra Server...")
        logger.info("=" * 60)

        # 1. Initialize storage backends
        await _initialize_storage(registry)

        # 2. Connect MCP tools
        await _connect_mcp_tools(registry)

        # 3. Run custom startup hook
        if custom_startup:
            try:
                result = custom_startup()
                if hasattr(result, "__await__"):
                    await result
                logger.info("Custom startup hook completed")
            except Exception as e:
                logger.error(f"Custom startup hook failed: {e}")
                raise LifecycleError(f"Custom startup hook failed: {e}") from e

        # Log startup summary
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"Astra Server started in {elapsed:.2f}s")
        logger.info(f"  Agents: {len(registry.agents)}")
        logger.info(f"  Storage backends: {len(registry.storage)}")
        logger.info(f"  MCP tools: {len(registry.mcp_tools)}")
        logger.info(f"  RAG pipelines: {len(registry.rag_pipelines)}")
        logger.info("=" * 60)

        yield

        # ═══════════════════════════════════════════════════════════════
        # SHUTDOWN
        # ═══════════════════════════════════════════════════════════════
        logger.info("=" * 60)
        logger.info("Shutting down Astra Server...")
        logger.info("=" * 60)

        # 1. Run custom shutdown hook
        if custom_shutdown:
            try:
                result = custom_shutdown()
                if hasattr(result, "__await__"):
                    await result
                logger.info("Custom shutdown hook completed")
            except Exception as e:
                logger.warning(f"Custom shutdown hook error: {e}")

        # 2. Disconnect MCP tools
        await _disconnect_mcp_tools(registry)

        # 3. Disconnect storage backends
        await _disconnect_storage(registry)

        logger.info("Astra Server stopped")
        logger.info("=" * 60)

    return lifespan


async def _initialize_storage(registry: AgentRegistry) -> None:
    """
    Initialize all storage backends.

    Connects and creates tables. Fails loud on error.
    """
    for storage_info in registry.storage.values():
        storage = storage_info.instance
        storage_id = storage_info.id
        storage_type = storage_info.type_name

        try:
            # Connect
            if hasattr(storage, "connect"):
                await storage.connect()
                logger.info(f"Connected to {storage_type}: {storage_id}")

            # Create tables
            if hasattr(storage, "create_tables"):
                await storage.create_tables()
                logger.info(f"Tables initialized for: {storage_id}")

        except Exception as e:
            error_msg = (
                f"Failed to initialize storage '{storage_id}' ({storage_type}).\n"
                f"Error: {e}\n"
                f"Used by agents: {storage_info.used_by}\n"
                f"\nPossible fixes:\n"
                f"  - Check your connection string\n"
                f"  - Ensure the database server is running\n"
                f"  - Verify credentials and permissions"
            )
            logger.error(error_msg)
            raise StorageConnectionError(error_msg) from e


async def _connect_mcp_tools(registry: AgentRegistry) -> None:
    """
    Connect all MCP tools.

    Fails loud on error.
    """
    for tool in registry.mcp_tools:
        tool_name = getattr(tool, "name", "unnamed")

        try:
            if hasattr(tool, "connect"):
                await tool.connect()
                logger.info(f"Connected MCP tool: {tool_name}")
            elif hasattr(tool, "start"):
                await tool.start()
                logger.info(f"Started MCP tool: {tool_name}")

        except Exception as e:
            error_msg = (
                f"Failed to connect MCP tool '{tool_name}'.\n"
                f"Error: {e}\n"
                f"\nPossible fixes:\n"
                f"  - Check the MCP server configuration\n"
                f"  - Ensure the MCP server is accessible\n"
                f"  - Verify any required API keys are set"
            )
            logger.error(error_msg)
            raise MCPConnectionError(error_msg) from e


async def _disconnect_mcp_tools(registry: AgentRegistry) -> None:
    """
    Disconnect all MCP tools.

    Logs warnings on error (doesn't fail).
    """
    for tool in registry.mcp_tools:
        tool_name = getattr(tool, "name", "unnamed")

        try:
            if hasattr(tool, "close"):
                await tool.close()
                logger.info(f"Disconnected MCP tool: {tool_name}")
            elif hasattr(tool, "stop"):
                await tool.stop()
                logger.info(f"Stopped MCP tool: {tool_name}")

        except Exception as e:
            logger.warning(f"Error disconnecting MCP tool '{tool_name}': {e}")


async def _disconnect_storage(registry: AgentRegistry) -> None:
    """
    Disconnect all storage backends.

    Logs warnings on error (doesn't fail).
    """
    for storage_info in registry.storage.values():
        storage = storage_info.instance
        storage_id = storage_info.id

        try:
            if hasattr(storage, "disconnect"):
                await storage.disconnect()
                logger.info(f"Disconnected storage: {storage_id}")

        except Exception as e:
            logger.warning(f"Error disconnecting storage '{storage_id}': {e}")
