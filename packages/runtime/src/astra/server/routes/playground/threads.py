"""
Playground Thread and Message Routes.

Provides /api/threads/* and /api/agents/{name}/threads/* endpoints.
Uses agent's storage backend (LibSQL, PostgreSQL, etc.) for persistence.
"""

from collections.abc import AsyncIterator
import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from astra.server.registry import AgentRegistry


logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateThreadRequest(BaseModel):
    """Request to create a new thread."""

    title: str | None = Field(None, description="Optional thread title")


class ThreadResponse(BaseModel):
    """Thread info response."""

    id: str
    agent_name: str | None
    title: str | None
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    """Message info response."""

    id: str
    thread_id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    created_at: str


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    content: str = Field(..., description="Message content")


class GenerateRequest(BaseModel):
    """Request to generate AI response."""

    message: str = Field(..., description="User message to respond to")


# ============================================================================
# Helper Functions
# ============================================================================


def _get_agent_storage(registry: AgentRegistry, agent_name: str):
    """Get storage from agent, raise 404 if agent not found."""
    agent = registry.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    storage = getattr(agent, "storage", None)
    if not storage:
        raise HTTPException(
            status_code=500, detail=f"Agent '{agent_name}' has no storage configured"
        )
    return agent, storage


# ============================================================================
# Router Factory
# ============================================================================


def create_threads_router(registry: AgentRegistry) -> APIRouter:
    """
    Create router for thread and message endpoints.

    Args:
        registry: AgentRegistry with all agents

    Returns:
        FastAPI APIRouter for thread/message endpoints
    """
    router = APIRouter(tags=["Playground - Threads"])

    # ========================================================================
    # Thread Endpoints
    # ========================================================================

    @router.get("/agents/{agent_name}/threads", response_model=list[ThreadResponse])
    async def list_agent_threads(agent_name: str) -> list[ThreadResponse]:
        """List all threads for an agent."""
        _, storage = _get_agent_storage(registry, agent_name)

        threads = await storage.list_threads(agent_name=agent_name)
        return [
            ThreadResponse(
                id=t.id,
                agent_name=t.agent_name,
                title=t.title,
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat(),
            )
            for t in threads
        ]

    @router.post("/agents/{agent_name}/threads", response_model=ThreadResponse)
    async def create_agent_thread(
        agent_name: str,
        request: CreateThreadRequest | None = None,
    ) -> ThreadResponse:
        """Create a new thread for an agent."""
        _, storage = _get_agent_storage(registry, agent_name)

        title = request.title if request else None
        thread = await storage.create_thread(agent_name=agent_name, title=title)

        return ThreadResponse(
            id=thread.id,
            agent_name=agent_name,
            title=thread.title,
            created_at=thread.created_at.isoformat(),
            updated_at=thread.updated_at.isoformat(),
        )

    @router.get("/threads/{thread_id}", response_model=ThreadResponse)
    async def get_thread(thread_id: str) -> ThreadResponse:
        """Get a thread by ID."""
        # Find the thread in any agent's storage
        for agent in registry.agents.values():
            storage = getattr(agent, "storage", None)
            if storage:
                thread = await storage.get_thread(thread_id)
                if thread:
                    return ThreadResponse(
                        id=thread.id,
                        agent_name=thread.agent_name,
                        title=thread.title,
                        created_at=thread.created_at.isoformat(),
                        updated_at=thread.updated_at.isoformat(),
                    )

        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    @router.delete("/threads/{thread_id}")
    async def delete_thread(thread_id: str) -> dict[str, bool]:
        """Delete a thread and all its messages."""
        # Find and delete the thread from any agent's storage
        for agent in registry.agents.values():
            storage = getattr(agent, "storage", None)
            if storage:
                thread = await storage.get_thread(thread_id)
                if thread:
                    await storage.soft_delete_thread(thread_id)
                    return {"deleted": True}

        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    # ========================================================================
    # Message Endpoints
    # ========================================================================

    @router.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
    async def get_thread_messages(thread_id: str) -> list[MessageResponse]:
        """Get all messages in a thread."""
        # Find the thread and its messages
        for agent in registry.agents.values():
            storage = getattr(agent, "storage", None)
            if storage:
                thread = await storage.get_thread(thread_id)
                if thread:
                    messages = await storage.get_history(thread_id, limit=100)
                    return [
                        MessageResponse(
                            id=m.id,
                            thread_id=m.thread_id,
                            role=m.role,
                            content=m.content,
                            tool_calls=m.metadata.get("tool_calls"),
                            created_at=m.created_at.isoformat(),
                        )
                        for m in messages
                    ]

        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    @router.post("/threads/{thread_id}/messages", response_model=MessageResponse)
    async def add_message(
        thread_id: str,
        request: SendMessageRequest,
    ) -> MessageResponse:
        """Add a user message to a thread."""
        from datetime import datetime, timezone
        import uuid

        # Find the thread's storage
        for agent in registry.agents.values():
            storage = getattr(agent, "storage", None)
            if storage:
                thread = await storage.get_thread(thread_id)
                if thread:
                    await storage.add_message(
                        thread_id=thread_id,
                        role="user",
                        content=request.content,
                    )
                    # Flush the queue to persist immediately
                    await storage.queue.flush()

                    # Return the message info
                    return MessageResponse(
                        id=f"msg-{uuid.uuid4().hex[:12]}",
                        thread_id=thread_id,
                        role="user",
                        content=request.content,
                        tool_calls=None,
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )

        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    @router.post("/threads/{thread_id}/generate")
    async def generate_response(
        thread_id: str,
        request: GenerateRequest,
    ) -> StreamingResponse:
        """Generate AI response and stream it."""
        # Find the thread and its agent
        found_agent = None
        found_storage = None

        for agent in registry.agents.values():
            storage = getattr(agent, "storage", None)
            if storage:
                thread = await storage.get_thread(thread_id)
                if thread:
                    found_agent = agent
                    found_storage = storage
                    break

        if not found_agent or not found_storage:
            raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

        # Add user message first (persisted)
        await found_storage.add_message(
            thread_id=thread_id,
            role="user",
            content=request.message,
        )
        await found_storage.queue.flush()

        async def event_generator() -> AsyncIterator[str]:
            """Generate SSE events and save response."""
            full_response = ""

            try:
                if hasattr(found_agent, "stream"):
                    async for chunk in found_agent.stream(request.message):
                        chunk_str = str(chunk)
                        full_response += chunk_str
                        data = {"content": chunk_str}
                        yield f"data: {json.dumps(data)}\n\n"
                else:
                    response = await found_agent.invoke(request.message)
                    full_response = str(response)
                    data = {"content": full_response}
                    yield f"data: {json.dumps(data)}\n\n"

                # Save assistant response to storage
                await found_storage.add_message(
                    thread_id=thread_id,
                    role="assistant",
                    content=full_response,
                )
                await found_storage.queue.flush()

                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Generate error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router
