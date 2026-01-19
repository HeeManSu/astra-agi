"""App lifespan management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan.

    Handles startup and shutdown events.
    TODO: Add proper lifecycle management when needed:
        - Database connection pooling
        - Agent startup/shutdown hooks
        - Cache warming
    """
    # Startup
    print("🚀 Astra Server started")  # noqa: T201

    yield

    # Shutdown
    print("👋 Astra Server stopped")  # noqa: T201
