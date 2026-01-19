"""
Astra Runtime - Embedded server for running AI agents.

Usage:
    from runtime import AstraServer

    server = AstraServer(
        agents=[my_agent],
        teams=[my_team],
    )

    app = server.get_app()
"""

from runtime.server import AstraServer


__version__ = "0.1.0"

__all__ = [
    "AstraServer",
]
