"""App lifespan management."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from os import PathLike
import sys
import time
from typing import Any

from fastapi import FastAPI
from framework.tool.mcp.toolkit import MCPToolkit
from observability.storage.sqlite import TelemetrySQLite


_connected_mcp_toolkits: list[MCPToolkit] = []


def _now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


async def _emit_lifecycle_event(
    app: FastAPI,
    phase: str,
    status: str,
    detail: str | None = None,
) -> None:
    """Update runtime_health checkpoints for health endpoints."""
    runtime_health = getattr(app.state, "runtime_health", None)
    if not isinstance(runtime_health, dict):
        return

    startup = runtime_health.get("startup", {})
    startup["phase"] = phase
    startup.setdefault("checkpoints", []).append(
        {
            "phase": phase,
            "status": status,
            "detail": detail,
            "timestamp": _now_iso(),
        }
    )


def _init_runtime_health_state(app: FastAPI, require_mcp_sync: bool) -> None:
    """Initialize startup/readiness/liveness state used by health endpoints."""
    now = _now_iso()
    app.state.runtime_health = {
        "liveness": {
            "status": "alive",
            "updated_at": now,
        },
        "readiness": {
            "status": "not_ready",
            "ready": False,
            "degraded": False,
            "reason": "startup_in_progress",
            "updated_at": now,
        },
        "startup": {
            "status": "starting",
            "phase": "initializing",
            "required_mcp_sync": require_mcp_sync,
            "started_at": now,
            "completed_at": None,
            "error": None,
            "checkpoints": [],
        },
        "sync": {
            "mcp_connect": {},
            "report": None,
        },
    }


def _set_readiness(app: FastAPI, *, ready: bool, degraded: bool, reason: str) -> None:
    """Update readiness state in app health."""
    runtime_health = getattr(app.state, "runtime_health", None)
    if not isinstance(runtime_health, dict):
        return

    runtime_health["readiness"] = {
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "degraded": degraded,
        "reason": reason,
        "updated_at": _now_iso(),
    }


def _mark_startup_completed(app: FastAPI, *, degraded: bool, reason: str) -> None:
    """Mark startup as completed and update readiness."""
    runtime_health = getattr(app.state, "runtime_health", None)
    if not isinstance(runtime_health, dict):
        return

    startup = runtime_health.get("startup", {})
    startup["status"] = "completed"
    startup["completed_at"] = _now_iso()
    _set_readiness(app, ready=True, degraded=degraded, reason=reason)


def _mark_startup_failed(app: FastAPI, error: str) -> None:
    """Mark startup as failed and not ready."""
    runtime_health = getattr(app.state, "runtime_health", None)
    if not isinstance(runtime_health, dict):
        return

    startup = runtime_health.get("startup", {})
    startup["status"] = "failed"
    startup["error"] = error
    startup["completed_at"] = _now_iso()
    _set_readiness(app, ready=False, degraded=True, reason=error)


def _mark_shutdown(app: FastAPI) -> None:
    """Mark the process as shutting down."""
    runtime_health = getattr(app.state, "runtime_health", None)
    if not isinstance(runtime_health, dict):
        return

    runtime_health["liveness"] = {"status": "stopping", "updated_at": _now_iso()}
    _set_readiness(app, ready=False, degraded=False, reason="shutdown")


def _toolkit_key(toolkit: MCPToolkit) -> tuple[str, str, tuple[str, ...]]:
    """Build a stable dedupe key for MCP toolkit instances."""
    raw_slug = getattr(toolkit, "slug", None)
    if not isinstance(raw_slug, str) or not raw_slug.strip():
        raise RuntimeError("MCP toolkit slug is required for startup dedupe.")
    slug = raw_slug.strip()
    return (
        slug,
        "",
        (),
    )


def _get_all_mcp_toolkits() -> list[MCPToolkit]:
    """Collect all MCP toolkits from registered agents and teams."""
    from runtime.registry import agent_registry, team_registry

    toolkits: list[MCPToolkit] = []
    seen_keys: set[tuple[str, str, tuple[str, ...]]] = set()

    for agent in agent_registry.list_all():
        for tool in agent.tools or []:
            if not isinstance(tool, MCPToolkit):
                continue
            tool_key = _toolkit_key(tool)
            if tool_key in seen_keys:
                continue
            toolkits.append(tool)
            seen_keys.add(tool_key)

    for team in team_registry.list_all():
        for member in getattr(team, "flat_members", []) or []:
            agent = getattr(member, "agent", member)
            for tool in getattr(agent, "tools", []) or []:
                if not isinstance(tool, MCPToolkit):
                    continue
                tool_key = _toolkit_key(tool)
                if tool_key in seen_keys:
                    continue
                toolkits.append(tool)
                seen_keys.add(tool_key)

    return toolkits


async def _connect_mcp_with_retry(
    toolkit: MCPToolkit,
    *,
    timeout_seconds: float,
    retries: int,
    retry_backoff_seconds: float,
) -> tuple[bool, str | None, int]:
    """Connect to an MCP toolkit with timeout and bounded retries."""
    attempts = max(retries, 0) + 1
    for attempt in range(attempts):
        try:
            await asyncio.wait_for(toolkit.connect(), timeout=timeout_seconds)
            return True, None, attempt + 1
        except Exception as e:  # noqa: PERF203
            if attempt < attempts - 1:
                await asyncio.sleep(retry_backoff_seconds * (2**attempt))
                continue
            return False, str(e), attempt + 1
    return False, "connect retry loop exited unexpectedly", attempts


async def _close_connected_mcp_toolkits() -> None:
    """Close all tracked MCP toolkit connections."""
    global _connected_mcp_toolkits

    for toolkit in _connected_mcp_toolkits:
        try:
            await toolkit.close()
        except Exception:  # noqa: PERF203
            pass
    _connected_mcp_toolkits.clear()


async def _close_observability(app: FastAPI) -> None:
    """Close observability engine storage if available."""
    obs = getattr(app.state, "observability", None)
    if obs:
        await obs.storage.close()


def _resolve_startup_sync_config(app: FastAPI) -> dict[str, Any]:
    """Extract and validate startup sync configuration from app state."""
    startup_sync_config = getattr(app.state, "startup_sync_config", None)
    cfg = {
        "require_mcp_sync": bool(getattr(startup_sync_config, "require_mcp_sync", True)),
        "mcp_connect_timeout_seconds": float(
            getattr(startup_sync_config, "mcp_connect_timeout_seconds", 10.0)
        ),
        "mcp_connect_concurrency": int(getattr(startup_sync_config, "mcp_connect_concurrency", 10)),
        "mcp_list_timeout_seconds": float(
            getattr(startup_sync_config, "mcp_list_timeout_seconds", 10.0)
        ),
        "mcp_retries": int(getattr(startup_sync_config, "mcp_retries", 2)),
        "mcp_retry_backoff_seconds": float(
            getattr(startup_sync_config, "mcp_retry_backoff_seconds", 0.5)
        ),
    }

    if cfg["mcp_connect_timeout_seconds"] <= 0:
        raise RuntimeError("startup_sync.mcp_connect_timeout_seconds must be > 0")
    if cfg["mcp_list_timeout_seconds"] <= 0:
        raise RuntimeError("startup_sync.mcp_list_timeout_seconds must be > 0")
    if cfg["mcp_retries"] < 0:
        raise RuntimeError("startup_sync.mcp_retries must be >= 0")
    if cfg["mcp_retry_backoff_seconds"] < 0:
        raise RuntimeError("startup_sync.mcp_retry_backoff_seconds must be >= 0")
    if cfg["mcp_connect_concurrency"] <= 0:
        raise RuntimeError("startup_sync.mcp_connect_concurrency must be > 0")

    return cfg


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan.

    Startup order:
        1. Observability (before trace — uses stdout fallback)
        2. Storage       (traced)
        3. MCP connect   (traced)
        4. Tool sync     (traced)

    Each node independently syncs its MCP connections and tools.
    Tool writes are idempotent upserts, so concurrent syncs are safe.

    Shutdown order:
        1. MCP connections
        2. Storage
        3. Observability
    """
    from framework.storage.client import StorageClient
    from observability import LogLevel, log, span, trace

    from runtime.registry import storage_registry

    cfg = _resolve_startup_sync_config(app)
    require_mcp_sync = cfg["require_mcp_sync"]

    _connected_mcp_toolkits.clear()
    _init_runtime_health_state(app, require_mcp_sync=require_mcp_sync)

    # --- Startup ---
    storage = storage_registry.get_default()
    t0 = time.monotonic()

    try:
        # Phase 1: Initialize Observability (before trace — stdout only)
        await _emit_lifecycle_event(app, phase="observability", status="in_progress")
        telemetry_config = getattr(app.state, "telemetry_config", None)
        if telemetry_config and telemetry_config.enabled:
            try:
                from observability import ObservabilityEngine, init

                if isinstance(telemetry_config.db_path, (str, PathLike)):
                    sqlite_path = str(telemetry_config.db_path)
                    obs_storage = TelemetrySQLite(sqlite_path)
                    storage_label = sqlite_path
                elif hasattr(telemetry_config.db_path, "init") and hasattr(
                    telemetry_config.db_path, "close"
                ):
                    obs_storage = telemetry_config.db_path
                    storage_label = telemetry_config.db_path.__class__.__name__
                else:
                    raise TypeError(
                        "TelemetryConfig.db_path must be a string/path-like value or an observability storage backend "
                        f"with init()/close(); got {type(telemetry_config.db_path)}"
                    )

                await obs_storage.init()
                obs_engine = ObservabilityEngine(obs_storage, debug_mode=telemetry_config.debug)
                app.state.observability = obs_engine
                init(obs_engine)

                await _emit_lifecycle_event(
                    app,
                    phase="observability",
                    status="completed",
                    detail=f"storage={storage_label}",
                )
                sys.stdout.write(f"Observability initialized (storage: {storage_label})\n")
            except ImportError:
                app.state.observability = None
                await _emit_lifecycle_event(
                    app, phase="observability", status="skipped", detail="module_not_installed"
                )
                raise RuntimeError(
                    "Telemetry is enabled but observability package is not installed/available."
                ) from None
            except Exception as e:
                app.state.observability = None
                await _emit_lifecycle_event(
                    app, phase="observability", status="failed", detail=str(e)
                )
                raise RuntimeError(f"Telemetry initialization failed: {e}") from e
        else:
            app.state.observability = None
            await _emit_lifecycle_event(
                app, phase="observability", status="skipped", detail="disabled"
            )

        # Phases 2-4 inside a startup trace (no-op if engine was not initialized)
        async with trace("server.startup", attributes={"require_mcp_sync": require_mcp_sync}):
            # Phase 2: Connect Storage
            async with span("storage.connect"):
                await _emit_lifecycle_event(app, phase="storage_connect", status="in_progress")
                await log(LogLevel.INFO, "Connecting storage backend")

                if storage is None:
                    raise RuntimeError("Storage backend is required but not configured")
                if not isinstance(storage, StorageClient):
                    raise RuntimeError(
                        "Invalid storage backend configured. Expected StorageClient for runtime startup."
                    )

                await storage.connect()
                storage_type = type(getattr(storage, "storage", storage)).__name__
                await log(LogLevel.DEBUG, f"Storage type: {storage_type}")
                await log(LogLevel.INFO, "Storage connected")
                await _emit_lifecycle_event(app, phase="storage_connect", status="completed")

                if getattr(storage, "storage", None) is None:
                    raise RuntimeError(
                        "Storage backend is required but missing from StorageClient."
                    )

            # Phase 3: MCP Connect
            failed_mcp_connects: list[str] = []
            failed_sync_servers: list[str] = []
            tool_sync_report: dict[str, Any] | None = None

            mcp_connect_timeout_seconds = cfg["mcp_connect_timeout_seconds"]
            mcp_connect_concurrency = cfg["mcp_connect_concurrency"]
            mcp_list_timeout_seconds = cfg["mcp_list_timeout_seconds"]
            mcp_retries = cfg["mcp_retries"]
            mcp_retry_backoff_seconds = cfg["mcp_retry_backoff_seconds"]

            async with span("mcp.connect", attributes={"concurrency": mcp_connect_concurrency}):
                await _emit_lifecycle_event(app, phase="mcp_connect", status="in_progress")
                mcp_toolkits = _get_all_mcp_toolkits()
                await log(
                    LogLevel.INFO,
                    f"Connecting {len(mcp_toolkits)} MCP toolkits (concurrency={mcp_connect_concurrency})",
                )

                # Deduplicate slugs
                seen_mcp_slugs: dict[str, int] = {}
                for toolkit in mcp_toolkits:
                    raw_slug = getattr(toolkit, "slug", None)
                    if not isinstance(raw_slug, str) or not raw_slug.strip():
                        raise RuntimeError("MCP toolkit slug is required during startup.")
                    slug = raw_slug.strip()
                    existing_obj_id = seen_mcp_slugs.get(slug)
                    if existing_obj_id is not None and existing_obj_id != id(toolkit):
                        raise RuntimeError(
                            f"Duplicate MCP toolkit slug '{slug}' detected. MCP slugs must be unique."
                        )
                    seen_mcp_slugs[slug] = id(toolkit)

                semaphore = asyncio.Semaphore(mcp_connect_concurrency)

                async def connect_one(
                    toolkit: MCPToolkit,
                ) -> tuple[MCPToolkit, str, bool, str | None, int]:
                    raw_command = getattr(toolkit, "command", "")
                    command = "" if raw_command is None else str(raw_command)
                    raw_args = getattr(toolkit, "args", None)
                    if isinstance(raw_args, (list, tuple)):
                        args_text = " ".join(str(arg) for arg in raw_args)
                    else:
                        args_text = ""
                    key = "|".join([toolkit.name, command, args_text])
                    await log(
                        LogLevel.DEBUG,
                        f"Connecting '{toolkit.name}' (retries={mcp_retries})",
                        attributes={"slug": getattr(toolkit, "slug", ""), "command": command},
                    )
                    async with semaphore:
                        ok, error, attempts = await _connect_mcp_with_retry(
                            toolkit,
                            timeout_seconds=mcp_connect_timeout_seconds,
                            retries=mcp_retries,
                            retry_backoff_seconds=mcp_retry_backoff_seconds,
                        )
                    return toolkit, key, ok, error, attempts

                connect_results = await asyncio.gather(
                    *(connect_one(toolkit) for toolkit in mcp_toolkits)
                )
                for toolkit, key, ok, error, attempts in connect_results:
                    raw_command = getattr(toolkit, "command", "")
                    command = "" if raw_command is None else str(raw_command)
                    raw_args = getattr(toolkit, "args", None)
                    if isinstance(raw_args, (list, tuple)):
                        args_text = " ".join(str(arg) for arg in raw_args)
                    else:
                        args_text = ""

                    app.state.runtime_health["sync"]["mcp_connect"][key] = {
                        "name": toolkit.name,
                        "slug": getattr(toolkit, "slug", None),
                        "command": command,
                        "args": args_text,
                        "connected": ok,
                        "attempts": attempts,
                        "error": error,
                        "updated_at": _now_iso(),
                    }

                    if ok:
                        _connected_mcp_toolkits.append(toolkit)
                        await log(
                            LogLevel.INFO,
                            f"Connected '{toolkit.name}' ({attempts} attempt{'s' if attempts != 1 else ''})",
                        )
                    else:
                        failed_mcp_connects.append(toolkit.name)
                        await log(
                            LogLevel.ERROR,
                            f"Failed to connect '{toolkit.name}': {error}",
                            attributes={"attempts": attempts},
                        )

                ok_count = len(mcp_toolkits) - len(failed_mcp_connects)
                await log(
                    LogLevel.INFO,
                    f"MCP connect: {ok_count} ok, {len(failed_mcp_connects)} failed",
                )
                await _emit_lifecycle_event(
                    app,
                    phase="mcp_connect",
                    status="completed" if not failed_mcp_connects else "failed",
                    detail=f"failed={failed_mcp_connects}"
                    if failed_mcp_connects
                    else "all_connected",
                )

                if failed_mcp_connects and require_mcp_sync:
                    raise RuntimeError(
                        f"MCP connect failed for: {', '.join(sorted(set(failed_mcp_connects)))}"
                    )

            # Phase 4: Tool Sync
            async with span("tools.sync"):
                await _emit_lifecycle_event(app, phase="tool_sync", status="in_progress")
                await log(LogLevel.INFO, "Syncing tools to database")

                astra_server = getattr(app.state, "astra_server", None)
                if astra_server and hasattr(astra_server, "sync_tools"):
                    report = await astra_server.sync_tools(
                        mcp_list_timeout_seconds=mcp_list_timeout_seconds,
                        mcp_retries=mcp_retries,
                        mcp_retry_backoff_seconds=mcp_retry_backoff_seconds,
                    )
                    if isinstance(report, dict):
                        tool_sync_report = report
                    app.state.runtime_health["sync"]["report"] = tool_sync_report
                    failed_sync_servers = [
                        server
                        for server, server_report in (tool_sync_report or {}).get("mcp", {}).items()
                        if isinstance(server_report, dict)
                        and server_report.get("status") == "failed"
                    ]
                    await log(LogLevel.DEBUG, f"Sync report: {tool_sync_report}")
                    await log(LogLevel.INFO, "Tool sync completed")
                    await _emit_lifecycle_event(
                        app,
                        phase="tool_sync",
                        status="completed" if not failed_sync_servers else "failed",
                        detail=f"failed={failed_sync_servers}"
                        if failed_sync_servers
                        else "all_synced",
                    )
                else:
                    await log(LogLevel.WARN, "Tool sync skipped (no astra_server)")
                    await _emit_lifecycle_event(
                        app, phase="tool_sync", status="skipped", detail="runtime_missing"
                    )

                if failed_sync_servers and require_mcp_sync:
                    raise RuntimeError(
                        f"MCP sync failed for: {', '.join(sorted(set(failed_sync_servers)))}"
                    )

        # Final status
        if (failed_mcp_connects or failed_sync_servers) and require_mcp_sync:
            all_failures = sorted(set(failed_mcp_connects + failed_sync_servers))
            raise RuntimeError(f"Startup sync reported failures: {', '.join(all_failures)}")

        degraded = bool(failed_mcp_connects or failed_sync_servers)
        _mark_startup_completed(
            app,
            degraded=degraded,
            reason="ready_degraded" if degraded else "ready",
        )

        elapsed = time.monotonic() - t0
        sys.stdout.write(f"Astra Server started ({elapsed:.2f}s)\n")

    except Exception as e:
        await _emit_lifecycle_event(app, phase="startup", status="failed", detail=str(e))
        _mark_startup_failed(app, str(e))
        try:
            await _close_connected_mcp_toolkits()
        except Exception as cleanup_err:
            sys.stdout.write(f"Startup cleanup MCP close failed: {cleanup_err}\n")
        try:
            if storage and hasattr(storage, "disconnect"):
                await storage.disconnect()
        except Exception as cleanup_err:
            sys.stdout.write(f"Startup cleanup storage disconnect failed: {cleanup_err}\n")
        try:
            await _close_observability(app)
        except Exception as cleanup_err:
            sys.stdout.write(f"Startup cleanup observability close failed: {cleanup_err}\n")
        raise

    yield

    # --- Shutdown ---
    _mark_shutdown(app)
    try:
        await _close_connected_mcp_toolkits()
    except Exception as e:
        sys.stdout.write(f"Shutdown MCP close failed: {e}\n")

    try:
        if storage and hasattr(storage, "disconnect"):
            await storage.disconnect()
    except Exception as e:
        sys.stdout.write(f"Shutdown storage disconnect failed: {e}\n")

    try:
        await _close_observability(app)
    except Exception as e:
        sys.stdout.write(f"Shutdown observability close failed: {e}\n")

    sys.stdout.write("Astra Server stopped\n")
