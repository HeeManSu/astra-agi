"""App module - FastAPI app creation and configuration."""

from runtime.app.app import create_app
from runtime.app.lifespan import app_lifespan


__all__ = [
    "app_lifespan",
    "create_app",
]
