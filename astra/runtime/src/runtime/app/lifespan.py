"""App lifespan management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan.

    Handles startup and shutdown events including:
        - Observability initialization (from TelemetryConfig in app.state)
        - Storage connection/disconnection
    """
    from runtime.registry import storage_registry

    # --- Startup ---

    # 1. Initialize Observability from TelemetryConfig (stored in app.state by create_app)
    telemetry_config = getattr(app.state, "telemetry_config", None)
    if telemetry_config and telemetry_config.enabled:
        try:
            from observability import ObservabilityEngine, SQLiteStorage

            obs_storage = SQLiteStorage(telemetry_config.db_path)
            await obs_storage.init()

            obs_engine = ObservabilityEngine(obs_storage)
            app.state.observability = obs_engine

            if telemetry_config.debug:
                print(f"📊 Observability initialized (db: {telemetry_config.db_path}, debug=True)")  # noqa: T201
            else:
                print(f"📊 Observability initialized (db: {telemetry_config.db_path})")  # noqa: T201
        except ImportError:
            app.state.observability = None
            print("⚠️  Observability not available (package not installed)")  # noqa: T201
        except Exception as e:
            app.state.observability = None
            print(f"⚠️  Observability init failed: {e}")  # noqa: T201
    else:
        app.state.observability = None
        if telemetry_config and not telemetry_config.enabled:
            print("📊 Observability disabled")  # noqa: T201

    # 2. Connect storage
    storage = storage_registry.get_default()
    if storage and hasattr(storage, "connect"):
        await storage.connect()

    print("🚀 Astra Server started")  # noqa: T201

    yield

    # --- Shutdown ---

    # 1. Disconnect storage
    if storage and hasattr(storage, "disconnect"):
        await storage.disconnect()

    # 2. Shutdown observability
    obs = getattr(app.state, "observability", None)
    if obs and hasattr(obs, "storage"):
        await obs.storage.close()
        print("Observability shutdown")  # noqa: T201

    print("Astra Server stopped")  # noqa: T201
