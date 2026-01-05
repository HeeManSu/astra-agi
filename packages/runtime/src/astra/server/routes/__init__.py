"""
Astra Server Routes Package.

Contains all route modules for the server.
"""

from astra.server.auth.routes import create_auth_router
from astra.server.routes.agents import create_agent_router
from astra.server.routes.meta import create_meta_router
from astra.server.routes.playground import create_playground_router
from astra.server.routes.threads import create_thread_router


__all__ = [
    "create_agent_router",
    "create_auth_router",
    "create_meta_router",
    "create_playground_router",
    "create_thread_router",
]
