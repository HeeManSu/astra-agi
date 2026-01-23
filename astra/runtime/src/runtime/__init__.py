"""
Astra Runtime - Embedded server for running AI agents.

Usage:
    from runtime import AstraServer, TelemetryConfig

    server = AstraServer(
        agents=[my_agent],
        teams=[my_team],
        telemetry=TelemetryConfig(enabled=True, db_path="./obs.db"),
    )

    app = server.get_app()
"""

from runtime.server import AstraServer, TelemetryConfig


__version__ = "0.1.0"

__all__ = [
    "AstraServer",
    "TelemetryConfig",
]
