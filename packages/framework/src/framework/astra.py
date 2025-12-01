"""
Astra Framework - Main orchestrator class.

This module contains:
- FrameworkSettings: Configuration settings
- AstraContext: Context for Astra applications.
- Astra: Main orchestrator class.
"""

from typing import Any

from observability import Observability
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class FrameworkSettings(BaseSettings):
    """Framework-level settings."""

    model_config = ConfigDict(env_file=".env", extra="allow")  # type: ignore[assignment]

    service_name: str = Field(default="astra", validation_alias="SERVICE_NAME")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    observability_log_file: str | None = Field(
        default="./jsons/astra_observability.json", validation_alias="ASTRA_OBSERVABILITY_LOG_FILE"
    )
    observability_log_level: str = Field(default="INFO", validation_alias="ASTRA_LOG_LEVEL")


class AstraContext:
    """
    Infrastructure root for Astra applications.

    Holds shared resources like settings, observability, and logger.
    This context is injected into agents to provide them with the necessary infrastructure.
    """

    def __init__(self, settings: FrameworkSettings | None = None):
        self.settings = settings or FrameworkSettings()

        # Initialize observability immediately
        self.observability = Observability.init(
            service_name=self.settings.service_name,
            log_level=self.settings.observability_log_level,
            enable_json_logs=True,
            log_file=self.settings.observability_log_file,
        )

        # Logger initialized from observability
        self.logger = self.observability.logger

    def shutdown(self) -> None:
        """Shutdown infrastructure."""
        if self.observability:
            self.observability.shutdown()


class Astra:
    """
    Global infrastructure manager for Astra.

    Provides shared resources like observability, logging, and configuration. Agents can use this infrastructure but are managed independently.

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

        # Create shared infrastructure (observability, logger, settings)
        self.context = AstraContext(settings)
        self._initialized = True

        # Logger from context
        self._logger = self.context.logger

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
