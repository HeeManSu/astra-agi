"""
Astra Server Routes Package.

Contains all route modules for the server.
"""

from astra.server.auth.routes import create_auth_router
from astra.server.routes.playground import create_playground_router


__all__ = [
    "create_auth_router",
    "create_playground_router",
]
