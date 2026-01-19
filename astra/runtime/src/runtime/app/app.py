"""FastAPI app factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from runtime.app.lifespan import app_lifespan


def create_app(
    title: str = "Astra Server",
    description: str = "AI Agent Server",
    version: str = "0.1.0",
    cors_allowed_origins: list[str] | None = None,
) -> FastAPI:
    """
    Create and configure a FastAPI application.

    Args:
        title: API title
        description: API description
        version: API version
        cors_allowed_origins: Allowed CORS origins

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=app_lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_allowed_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app
