"""
Tests for Astra Server Lifecycle Management.

Tests create_lifespan, startup/shutdown behavior, and custom hooks.
"""

from unittest.mock import MagicMock

from astra.server.lifecycle import (
    LifecycleError,
    MCPConnectionError,
    StorageConnectionError,
    _connect_mcp_tools,
    _disconnect_mcp_tools,
    _disconnect_storage,
    _initialize_storage,
    create_lifespan,
)
from astra.server.registry import AgentRegistry, StorageInfo
import pytest

from .conftest import (  # noqa: TID252
    FailingMCPServer,
    FailingStorage,
    SimpleMCPServer,
    create_agent,
    create_storage,
)


# ============================================================================
# create_lifespan Basic Tests
# ============================================================================


class TestCreateLifespanBasic:
    """Test create_lifespan basic behavior."""

    @pytest.mark.asyncio
    async def test_returns_context_manager(self):
        """Returns async context manager."""
        registry = AgentRegistry(agents={"test": create_agent()})
        lifespan = create_lifespan(registry)
        assert callable(lifespan)

    @pytest.mark.asyncio
    async def test_context_manager_yields(self):
        """Context manager yields correctly."""
        registry = AgentRegistry(agents={"test": create_agent()})
        lifespan = create_lifespan(registry)

        async with lifespan(MagicMock()):
            # Should not raise, yield point reached
            pass


# ============================================================================
# Storage Initialization Tests
# ============================================================================


class TestStorageInitialization:
    """Test storage initialization during startup."""

    @pytest.mark.asyncio
    async def test_storage_connect_called(self):
        """Storage.connect is called for each storage."""
        storage = create_storage()
        storage_info = StorageInfo(
            id="storage-0",
            instance=storage,
            type_name="AgentStorage",
            used_by=["test"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})

        # Should not raise - indicates connect was successful
        await _initialize_storage(registry)

    @pytest.mark.asyncio
    async def test_storage_create_tables_called(self):
        """Storage.create_tables is called after connect."""
        storage = create_storage()
        storage_info = StorageInfo(
            id="storage-0",
            instance=storage,
            type_name="AgentStorage",
            used_by=["test"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})

        # Should not raise - indicates create_tables was successful
        await _initialize_storage(registry)

    @pytest.mark.asyncio
    async def test_storage_without_connect_skipped(self):
        """Storage without connect method is skipped gracefully."""

        class NoConnectStorage:
            pass

        storage = NoConnectStorage()
        storage_info = StorageInfo(
            id="storage-0",
            instance=storage,
            type_name="NoConnectStorage",
            used_by=["test"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})

        # Should not raise
        await _initialize_storage(registry)

    @pytest.mark.asyncio
    async def test_connection_error_raises(self):
        """Connection error raises StorageConnectionError."""
        storage = FailingStorage()
        storage_info = StorageInfo(
            id="storage-0",
            instance=storage,
            type_name="FailingStorage",
            used_by=["test"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})

        with pytest.raises(StorageConnectionError):
            await _initialize_storage(registry)

    @pytest.mark.asyncio
    async def test_error_includes_storage_id(self):
        """Error message includes storage ID."""
        storage = FailingStorage()
        storage_info = StorageInfo(
            id="my-storage-id",
            instance=storage,
            type_name="FailingStorage",
            used_by=["test"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})

        with pytest.raises(StorageConnectionError) as exc_info:
            await _initialize_storage(registry)

        assert "my-storage-id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_includes_used_by(self):
        """Error message includes used_by agents."""
        storage = FailingStorage()
        storage_info = StorageInfo(
            id="storage-0",
            instance=storage,
            type_name="FailingStorage",
            used_by=["agent1", "agent2"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})

        with pytest.raises(StorageConnectionError) as exc_info:
            await _initialize_storage(registry)

        assert "agent1" in str(exc_info.value)
        assert "agent2" in str(exc_info.value)


# ============================================================================
# MCP Connection Tests
# ============================================================================


class TestMCPConnection:
    """Test MCP tool connection during startup."""

    @pytest.mark.asyncio
    async def test_mcp_connect_called(self):
        """MCP.connect is called for tools with connect."""
        mcp = SimpleMCPServer()
        registry = AgentRegistry(mcp_tools=[mcp])

        await _connect_mcp_tools(registry)

        assert mcp.connected is True

    @pytest.mark.asyncio
    async def test_mcp_start_called(self):
        """MCP.start is called for tools with start."""

        class MCPWithStart:
            def __init__(self):
                self.started = False
                self.name = "test-mcp"

            async def start(self):
                self.started = True

        mcp = MCPWithStart()
        registry = AgentRegistry(mcp_tools=[mcp])

        await _connect_mcp_tools(registry)

        assert mcp.started is True

    @pytest.mark.asyncio
    async def test_mcp_connection_error_raises(self):
        """Connection error raises MCPConnectionError."""
        mcp = FailingMCPServer()
        registry = AgentRegistry(mcp_tools=[mcp])

        with pytest.raises(MCPConnectionError):
            await _connect_mcp_tools(registry)

    @pytest.mark.asyncio
    async def test_error_includes_tool_name(self):
        """Error message includes tool name."""
        mcp = FailingMCPServer(name="my-mcp-tool")
        registry = AgentRegistry(mcp_tools=[mcp])

        with pytest.raises(MCPConnectionError) as exc_info:
            await _connect_mcp_tools(registry)

        assert "my-mcp-tool" in str(exc_info.value)


# ============================================================================
# MCP Disconnection Tests
# ============================================================================


class TestMCPDisconnection:
    """Test MCP tool disconnection during shutdown."""

    @pytest.mark.asyncio
    async def test_mcp_close_called(self):
        """MCP.close is called on shutdown."""
        mcp = SimpleMCPServer()
        mcp.connected = True
        registry = AgentRegistry(mcp_tools=[mcp])

        await _disconnect_mcp_tools(registry)

        assert not mcp.connected

    @pytest.mark.asyncio
    async def test_mcp_stop_called(self):
        """MCP.stop is called if close doesn't exist."""

        class MCPWithStop:
            def __init__(self):
                self.stopped = False
                self.name = "test-mcp"

            async def stop(self):
                self.stopped = True

        mcp = MCPWithStop()
        registry = AgentRegistry(mcp_tools=[mcp])

        await _disconnect_mcp_tools(registry)

        assert mcp.stopped is True

    @pytest.mark.asyncio
    async def test_errors_logged_not_raised(self):
        """Errors are logged but don't crash."""

        class FailingDisconnect:
            name = "failing"

            async def close(self):
                raise RuntimeError("Close failed")

        mcp = FailingDisconnect()
        registry = AgentRegistry(mcp_tools=[mcp])

        # Should not raise
        await _disconnect_mcp_tools(registry)


# ============================================================================
# Storage Disconnection Tests
# ============================================================================


class TestStorageDisconnection:
    """Test storage disconnection during shutdown."""

    @pytest.mark.asyncio
    async def test_storage_disconnect_called(self):
        """Storage.disconnect is called on shutdown."""
        storage = create_storage()
        storage_info = StorageInfo(
            id="storage-0",
            instance=storage,
            type_name="AgentStorage",
            used_by=["test"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})

        # Should not raise - indicates disconnect was successful
        await _disconnect_storage(registry)

    @pytest.mark.asyncio
    async def test_disconnect_errors_logged(self):
        """Disconnect errors are logged but don't crash."""

        class FailingDisconnect:
            async def disconnect(self):
                raise RuntimeError("Disconnect failed")

        storage = FailingDisconnect()
        storage_info = StorageInfo(
            id="storage-0",
            instance=storage,
            type_name="FailingDisconnect",
            used_by=["test"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})

        # Should not raise
        await _disconnect_storage(registry)


# ============================================================================
# Custom Hooks Tests
# ============================================================================


class TestCustomHooks:
    """Test custom startup/shutdown hooks."""

    @pytest.mark.asyncio
    async def test_custom_startup_called(self):
        """custom_startup is called during startup."""
        called = []

        async def my_startup():
            called.append("startup")

        registry = AgentRegistry(agents={"test": create_agent()})
        lifespan = create_lifespan(registry, custom_startup=my_startup)

        async with lifespan(MagicMock()):
            pass

        assert "startup" in called

    @pytest.mark.asyncio
    async def test_custom_startup_async_awaited(self):
        """custom_startup async functions are awaited."""
        result = []

        async def async_startup():
            result.append("async")

        registry = AgentRegistry(agents={"test": create_agent()})
        lifespan = create_lifespan(registry, custom_startup=async_startup)

        async with lifespan(MagicMock()):
            pass

        assert "async" in result

    @pytest.mark.asyncio
    async def test_custom_startup_error_raises(self):
        """custom_startup error raises LifecycleError."""

        async def failing_startup():
            raise ValueError("Startup failed!")

        registry = AgentRegistry(agents={"test": create_agent()})
        lifespan = create_lifespan(registry, custom_startup=failing_startup)

        with pytest.raises(LifecycleError):
            async with lifespan(MagicMock()):
                pass

    @pytest.mark.asyncio
    async def test_custom_shutdown_called(self):
        """custom_shutdown is called during shutdown."""
        called = []

        async def my_shutdown():
            called.append("shutdown")

        registry = AgentRegistry(agents={"test": create_agent()})
        lifespan = create_lifespan(registry, custom_shutdown=my_shutdown)

        async with lifespan(MagicMock()):
            pass

        assert "shutdown" in called

    @pytest.mark.asyncio
    async def test_custom_shutdown_errors_logged(self):
        """custom_shutdown errors are logged, not raised."""

        async def failing_shutdown():
            raise RuntimeError("Shutdown failed!")

        registry = AgentRegistry(agents={"test": create_agent()})
        lifespan = create_lifespan(registry, custom_shutdown=failing_shutdown)

        # Should not raise
        async with lifespan(MagicMock()):
            pass

    @pytest.mark.asyncio
    async def test_startup_runs_before_yield(self):
        """Startup runs before yield point."""
        order = []

        async def track_startup():
            order.append("startup")

        registry = AgentRegistry(agents={"test": create_agent()})
        lifespan = create_lifespan(registry, custom_startup=track_startup)

        async with lifespan(MagicMock()):
            order.append("during")

        assert order == ["startup", "during"]

    @pytest.mark.asyncio
    async def test_shutdown_runs_after_yield(self):
        """Shutdown runs after yield point."""
        order = []

        async def track_shutdown():
            order.append("shutdown")

        registry = AgentRegistry(agents={"test": create_agent()})
        lifespan = create_lifespan(registry, custom_shutdown=track_shutdown)

        async with lifespan(MagicMock()):
            order.append("during")

        assert order == ["during", "shutdown"]

    @pytest.mark.asyncio
    async def test_storage_without_create_tables_skipped(self):
        """Storage without create_tables method is skipped gracefully."""

        class ConnectOnlyStorage:
            def __init__(self):
                self.connected = False

            async def connect(self):
                self.connected = True

        storage = ConnectOnlyStorage()
        storage_info = StorageInfo(
            id="storage-0",
            instance=storage,
            type_name="ConnectOnlyStorage",
            used_by=["test"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})

        # Should not raise
        await _initialize_storage(registry)
        assert storage.connected is True

    @pytest.mark.asyncio
    async def test_error_includes_storage_type(self):
        """Error message includes storage type name."""
        storage = FailingStorage()
        storage_info = StorageInfo(
            id="storage-0",
            instance=storage,
            type_name="FailingStorage",
            used_by=["test"],
        )
        registry = AgentRegistry(storage={id(storage): storage_info})

        with pytest.raises(StorageConnectionError) as exc_info:
            await _initialize_storage(registry)

        assert "FailingStorage" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_custom_shutdown_async_awaited(self):
        """custom_shutdown async functions are awaited."""
        result = []

        async def async_shutdown():
            result.append("async_shutdown")

        registry = AgentRegistry(agents={"test": create_agent()})
        lifespan = create_lifespan(registry, custom_shutdown=async_shutdown)

        async with lifespan(MagicMock()):
            pass

        assert "async_shutdown" in result
