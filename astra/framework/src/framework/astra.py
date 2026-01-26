"""
Astra Framework - Main orchestrator class.

This module contains:
- FrameworkSettings: Configuration settings
- AstraContext: Context for Astra applications.
- Astra: Main orchestrator class.
"""

import logging
from typing import Any

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class FrameworkSettings(BaseSettings):
    """Framework-level settings."""

    model_config = ConfigDict(env_file=".env", extra="allow")  # type: ignore[assignment]

    service_name: str = Field(default="astra", validation_alias="SERVICE_NAME")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", validation_alias="ASTRA_LOG_LEVEL")


class AstraContext:
    """
    Infrastructure root for Astra applications.

    Holds shared resources like settings and logger.
    Observability (tracing) is handled by the runtime, not the framework.
    """

    def __init__(self, settings: FrameworkSettings | None = None):
        self.settings = settings or FrameworkSettings()

        # Setup standard Python logger
        self.logger = logging.getLogger(self.settings.service_name)
        self.logger.setLevel(self.settings.log_level.upper())

        # Add handler if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def shutdown(self) -> None:
        """Shutdown infrastructure."""
        # No cleanup needed for standard logging


class Astra:
    """
    Global infrastructure manager for Astra.

    Provides shared resources like logging and configuration.
    Observability (tracing) is handled by the runtime.

    Example:
     Initialize global infrastructure
     astra = Astra()
    """

    def __init__(self, settings: FrameworkSettings | None = None):
        """
        Initialize Astra global infrastructure.

        Args:
            settings: Optional framework settings
        """
        self.context = AstraContext(settings)
        self._initialized = True

    @property
    def logger(self) -> Any:
        """Get logger instance from context."""
        return self.context.logger

    async def shutdown(self) -> None:
        """Cleanup framework components."""
        if self.context:
            self.context.shutdown()
        self._initialized = False

    def __repr__(self) -> str:
        """String representation of the Astra instance."""
        return f"Astra(service={self.context.settings.service_name}, env={self.context.settings.environment})"
