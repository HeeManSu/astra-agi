"""
Playground Router Factory.

Creates the main playground router by combining all sub-routers.
"""

from fastapi import APIRouter

from astra.server.registry import AgentRegistry
from astra.server.routes.playground.agents import create_agents_router
from astra.server.routes.playground.threads import create_threads_router
from astra.server.routes.playground.tools import create_tools_router


def create_playground_router(registry: AgentRegistry) -> APIRouter:
    """
    Create the main playground router.

    Combines all playground sub-routers into a single /api prefix router.

    Args:
        registry: AgentRegistry with all agents

    Returns:
        FastAPI APIRouter with /api prefix
    """
    router = APIRouter(prefix="/api", tags=["Playground"])

    # Include agent-related endpoints
    agents_router = create_agents_router(registry)
    router.include_router(agents_router)

    # Include thread and message endpoints
    threads_router = create_threads_router(registry)
    router.include_router(threads_router)

    # Include tools endpoints
    tools_router = create_tools_router(registry)
    router.include_router(tools_router)

    return router
