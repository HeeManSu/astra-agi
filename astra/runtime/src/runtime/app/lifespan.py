"""App lifespan management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import sys

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
            from observability import ObservabilityEngine, init

            obs_storage = telemetry_config.db_path
            await obs_storage.init()

            obs_engine = ObservabilityEngine(obs_storage, debug_mode=telemetry_config.debug)
            app.state.observability = obs_engine

            # Wire engine to ContextVars-based instrument module
            init(obs_engine)

            if telemetry_config.debug:
                sys.stdout.write(
                    f"Observability initialized (db: {telemetry_config.db_path}, debug=True)"
                )
            else:
                sys.stdout.write(f"Observability initialized (db: {telemetry_config.db_path})")
        except ImportError:
            app.state.observability = None
            sys.stdout.write("Observability not available (package not installed)")
        except Exception as e:
            app.state.observability = None
            sys.stdout.write(f"Observability init failed: {e}")
    else:
        app.state.observability = None
        if telemetry_config and not telemetry_config.enabled:
            sys.stdout.write("Observability disabled")

    # 2. Connect storage
    storage = storage_registry.get_default()
    if storage and hasattr(storage, "connect"):
        await storage.connect()

    sys.stdout.write("Astra Server started")

    yield

    # --- Shutdown ---

    # 1. Disconnect storage
    if storage and hasattr(storage, "disconnect"):
        await storage.disconnect()

    # 2. Shutdown observability
    obs = getattr(app.state, "observability", None)
    if obs:
        await obs.storage.close()
        sys.stdout.write("Observability shutdown")

    sys.stdout.write("Astra Server stopped")
