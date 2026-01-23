"""FastAPI app factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from runtime.app.lifespan import app_lifespan


if TYPE_CHECKING:
    from runtime.server import TelemetryConfig


def create_app(
    title: str = "Astra Server",
    description: str = "AI Agent Server",
    version: str = "0.1.0",
    cors_allowed_origins: list[str] | None = None,
    telemetry_config: TelemetryConfig | None = None,
) -> FastAPI:
    """
    Create and configure a FastAPI application.

    Args:
        title: API title
        description: API description
        version: API version
        cors_allowed_origins: Allowed CORS origins
        telemetry_config: Telemetry configuration

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=app_lifespan,
    )

    # Store telemetry config in app.state (accessible in lifespan)
    app.state.telemetry_config = telemetry_config

    # CORS middleware
    if cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    return app
