"""
Astra Runtime - Embedded server for running AI agents.

Usage:
    from runtime import AstraServer, StartupSyncConfig, TelemetryConfig

    server = AstraServer(
        agents=[my_agent],
        teams=[my_team],
        telemetry=TelemetryConfig(enabled=True, db_path="./obs.db"),
        startup_sync=StartupSyncConfig(require_mcp_sync=True),
    )

    app = server.get_app()
"""

from runtime.server import AstraServer, StartupSyncConfig, TelemetryConfig


__version__ = "0.1.0"

__all__ = [
    "AstraServer",
    "StartupSyncConfig",
    "TelemetryConfig",
]
