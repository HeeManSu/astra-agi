"""
Playground Routes Package.

Provides /api/* endpoints for playground UI compatibility.
Organized into feature-based modules for maintainability.
"""

from astra.server.routes.playground.agents import create_agents_router
from astra.server.routes.playground.router import create_playground_router
from astra.server.routes.playground.threads import create_threads_router
from astra.server.routes.playground.tools import create_tools_router


__all__ = [
    "create_agents_router",
    "create_playground_router",
    "create_threads_router",
    "create_tools_router",
]
