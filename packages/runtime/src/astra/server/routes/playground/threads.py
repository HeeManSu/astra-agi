"""
Playground Thread and Message Routes.

Provides /api/v1/agents/{agentId}/threads and /api/v1/threads/* endpoints.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from framework.storage.memory import AgentStorage

from astra.server.registry import AgentRegistry


def create_threads_router(registry: AgentRegistry) -> APIRouter:
    """
    Create router for thread and message endpoints.

    Args:
        registry: AgentRegistry with all agents

    Returns:
        FastAPI APIRouter for thread/message endpoints
    """
    router = APIRouter(tags=["Threads"])

    @router.get("/agents/{agent_id}/threads")
    async def list_agent_threads(agent_id: str) -> list[dict[str, Any]]:
        """Get all threads for an agent."""
        agent = registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        storage = getattr(agent, "storage", None)
        if not storage:
            # Return empty list if agent has no storage (valid state)
            return []

        if not isinstance(storage, AgentStorage):
            storage = AgentStorage(storage=storage)

        actual_agent_id = getattr(agent, "id", None) or agent_id
        threads = await storage.list_threads(agent_name=actual_agent_id)
        return [
            {
                "id": thread.id,
                "agent_name": thread.agent_name,
                "title": thread.title,
                "created_at": thread.created_at.isoformat(),
                "updated_at": thread.updated_at.isoformat(),
            }
            for thread in threads
        ]

    @router.post("/agents/{agent_id}/threads")
    async def create_agent_thread(
        agent_id: str, request: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a new thread for an agent."""
        agent = registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        storage = getattr(agent, "storage", None)
        if not storage:
            raise HTTPException(
                status_code=400, detail=f"Agent '{agent_id}' has no storage configured"
            )

        if not isinstance(storage, AgentStorage):
            storage = AgentStorage(storage=storage)

        actual_agent_id = getattr(agent, "id", None) or agent_id

        # Generate title from first message if provided, otherwise use default
        title = None
        if request:
            title = request.get("title")
            # If no title but first message provided, generate title from it
            if not title and "message" in request:
                first_message = str(request["message"]).strip()
                if first_message:
                    # Truncate to 50 chars for title
                    title = first_message[:50] + ("..." if len(first_message) > 50 else "")

        # Default title if still None (fallback)
        if not title:
            title = f"New Thread {datetime.now().isoformat()}"

        thread = await storage.create_thread(agent_name=actual_agent_id, title=title)
        return {
            "id": thread.id,
            "agent_name": thread.agent_name,
            "title": thread.title,
            "created_at": thread.created_at.isoformat(),
            "updated_at": thread.updated_at.isoformat(),
        }

    @router.get("/threads/{thread_id}/messages")
    async def list_thread_messages(thread_id: str) -> list[dict[str, Any]]:
        """Get all messages for a thread."""
        found_storage = None
        for agent in registry.agents.values():
            storage = getattr(agent, "storage", None)
            if storage:
                if not isinstance(storage, AgentStorage):
                    storage = AgentStorage(storage=storage)

                thread = await storage.get_thread(thread_id)
                if thread:
                    found_storage = storage
                    break

        if not found_storage:
            raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

        messages = await found_storage.get_history(thread_id)
        return [
            {
                "id": message.id,
                "thread_id": message.thread_id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
            for message in messages
        ]

    return router
