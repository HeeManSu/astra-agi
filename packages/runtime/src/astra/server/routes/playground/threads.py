"""
Playground Thread Routes.

Provides /api/threads/* endpoints for conversation management.
"""

from datetime import datetime
import logging
from typing import Any
import uuid

from fastapi import APIRouter

from astra.server.registry import AgentRegistry


logger = logging.getLogger(__name__)


# ============================================================================
# Router Factory
# ============================================================================


def create_threads_router(registry: AgentRegistry) -> APIRouter:
    """
    Create router for thread-related playground endpoints.

    Args:
        registry: AgentRegistry with all agents

    Returns:
        FastAPI APIRouter for /threads endpoints
    """
    router = APIRouter(tags=["Playground - Threads"])

    @router.post("/threads")
    async def create_thread(body: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a new thread for chat."""
        body = body or {}
        thread_id = str(uuid.uuid4())
        return {
            "id": thread_id,
            "agent_id": body.get("agent_id"),
            "created_at": datetime.utcnow().isoformat(),
        }

    @router.get("/threads/{agent_id}")
    async def get_threads(agent_id: str) -> list[dict[str, Any]]:
        """Get threads for an agent (placeholder - returns empty for now)."""
        # TODO: Implement thread storage
        return []

    @router.get("/threads/{thread_id}/messages")
    async def get_messages(thread_id: str) -> list[dict[str, Any]]:
        """Get messages for a thread (placeholder - returns empty for now)."""
        # TODO: Implement message storage
        return []

    return router
