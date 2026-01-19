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
        - Storage connection/disconnection
    """
    from runtime.registry import storage_registry

    # Startup - connect storage
    storage = storage_registry.get_default()
    if storage and hasattr(storage, "connect"):
        await storage.connect()

    print("🚀 Astra Server started")  # noqa: T201

    yield

    # Shutdown - disconnect storage
    if storage and hasattr(storage, "disconnect"):
        await storage.disconnect()

    print("👋 Astra Server stopped")  # noqa: T201
