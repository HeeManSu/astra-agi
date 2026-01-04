"""
Thread Routes for Astra Server.

Provides /v1/threads endpoints for conversation management.
"""

from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from astra.server.registry import AgentRegistry


logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateThreadRequest(BaseModel):
    """Request body for creating a thread."""

    agent_name: str = Field(..., description="Name of the agent for this thread")
    metadata: dict[str, Any] | None = Field(None, description="Optional thread metadata")


class ThreadResponse(BaseModel):
    """Thread information."""

    id: str
    agent_name: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = None
    message_count: int = 0


class AddMessageRequest(BaseModel):
    """Request body for adding a message."""

    role: str = Field(..., description="Message role: user, assistant, system, or tool")
    content: str = Field(..., description="Message content")
    metadata: dict[str, Any] | None = Field(None, description="Optional message metadata")


class MessageResponse(BaseModel):
    """Message information."""

    id: str
    thread_id: str
    role: str
    content: str
    created_at: datetime
    metadata: dict[str, Any] | None = None


class ThreadListResponse(BaseModel):
    """Response for listing threads."""

    threads: list[ThreadResponse]
    total: int
    page: int
    per_page: int


class MessageListResponse(BaseModel):
    """Response for listing messages."""

    messages: list[MessageResponse]
    total: int


# ============================================================================
# Router Factory
# ============================================================================


def create_thread_router(registry: AgentRegistry) -> APIRouter:
    """
    Create router for thread endpoints.

    Args:
        registry: AgentRegistry with all resources

    Returns:
        FastAPI APIRouter
    """
    router = APIRouter(prefix="/v1/threads", tags=["Threads"])

    @router.get(
        "",
        response_model=ThreadListResponse,
        summary="List threads",
        description="Returns a paginated list of conversation threads",
    )
    async def list_threads(
        agent_name: str | None = Query(None, description="Filter by agent name"),
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    ) -> ThreadListResponse:
        """List all threads, optionally filtered by agent."""
        # Get storage from first agent or specified agent
        storage = None

        if agent_name:
            agent = registry.get_agent(agent_name)
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
            if hasattr(agent, "storage") and agent.storage:
                storage = agent.storage
        else:
            # Get storage from first agent that has it
            for agent in registry.agents.values():
                if hasattr(agent, "storage") and agent.storage:
                    storage = agent.storage
                    break

        if not storage:
            return ThreadListResponse(threads=[], total=0, page=page, per_page=per_page)

        try:
            # Build filter
            filter_dict = {}
            if agent_name:
                filter_dict["agent_name"] = agent_name

            # Query threads
            offset = (page - 1) * per_page
            query = storage.build_select_query(
                collection="astra_threads",
                filter_dict=filter_dict if filter_dict else None,
                sort=[("created_at", -1)],
                limit=per_page,
                offset=offset,
            )
            rows = await storage.fetch_all(query)

            # Parse into ThreadResponse objects
            threads = [
                ThreadResponse(
                    id=row["id"],
                    agent_name=row.get("agent_name", ""),
                    created_at=_parse_datetime(row.get("created_at")),
                    updated_at=_parse_datetime(row.get("updated_at")),
                    metadata=row.get("metadata"),
                    message_count=row.get("message_count", 0),
                )
                for row in rows
            ]

            # Get total count (simplified - just use len for now)
            total = len(threads)

            return ThreadListResponse(
                threads=threads,
                total=total,
                page=page,
                per_page=per_page,
            )

        except Exception as e:
            logger.error(f"Error listing threads: {e}")
            return ThreadListResponse(threads=[], total=0, page=page, per_page=per_page)

    @router.post(
        "",
        response_model=ThreadResponse,
        summary="Create thread",
        description="Create a new conversation thread",
    )
    async def create_thread(request: CreateThreadRequest) -> ThreadResponse:
        """Create a new thread for an agent."""
        agent = registry.get_agent(request.agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{request.agent_name}' not found")

        # Check if agent has storage
        if not hasattr(agent, "storage") or agent.storage is None:
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{request.agent_name}' does not have storage configured",
            )

        storage = agent.storage
        now = datetime.now(timezone.utc)
        thread_id = str(uuid.uuid4())

        try:
            # Insert thread
            thread_data = {
                "id": thread_id,
                "agent_name": request.agent_name,
                "created_at": now,
                "updated_at": now,
                "metadata": request.metadata,
                "message_count": 0,
            }

            query = storage.build_insert_query(collection="astra_threads", data=thread_data)
            await storage.execute(query)

            return ThreadResponse(
                id=thread_id,
                agent_name=request.agent_name,
                created_at=now,
                updated_at=now,
                metadata=request.metadata,
                message_count=0,
            )

        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create thread: {e!s}")

    @router.get(
        "/{thread_id}",
        response_model=ThreadResponse,
        summary="Get thread",
        description="Get a specific thread by ID",
    )
    async def get_thread(thread_id: str) -> ThreadResponse:
        """Get a thread by ID."""
        # Find storage that has this thread
        storage = None
        for agent in registry.agents.values():
            if hasattr(agent, "storage") and agent.storage:
                storage = agent.storage
                break

        if not storage:
            raise HTTPException(status_code=404, detail="No storage configured")

        try:
            query = storage.build_select_query(
                collection="astra_threads",
                filter_dict={"id": thread_id},
            )
            row = await storage.fetch_one(query)

            if not row:
                raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

            return ThreadResponse(
                id=row["id"],
                agent_name=row.get("agent_name", ""),
                created_at=_parse_datetime(row.get("created_at")),
                updated_at=_parse_datetime(row.get("updated_at")),
                metadata=row.get("metadata"),
                message_count=row.get("message_count", 0),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting thread: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get thread: {e!s}")

    @router.delete(
        "/{thread_id}",
        summary="Delete thread",
        description="Delete a thread and all its messages",
    )
    async def delete_thread(thread_id: str) -> dict[str, str]:
        """Delete a thread."""
        storage = None
        for agent in registry.agents.values():
            if hasattr(agent, "storage") and agent.storage:
                storage = agent.storage
                break

        if not storage:
            raise HTTPException(status_code=404, detail="No storage configured")

        try:
            # Delete messages first
            msg_query = storage.build_delete_query(
                collection="astra_messages",
                filter_dict={"thread_id": thread_id},
            )
            await storage.execute(msg_query)

            # Delete thread
            thread_query = storage.build_delete_query(
                collection="astra_threads",
                filter_dict={"id": thread_id},
            )
            await storage.execute(thread_query)

            return {"message": f"Thread '{thread_id}' deleted"}

        except Exception as e:
            logger.error(f"Error deleting thread: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete thread: {e!s}")

    @router.get(
        "/{thread_id}/messages",
        response_model=MessageListResponse,
        summary="List messages",
        description="Get all messages in a thread",
    )
    async def list_messages(thread_id: str) -> MessageListResponse:
        """List all messages in a thread."""
        storage = None
        for agent in registry.agents.values():
            if hasattr(agent, "storage") and agent.storage:
                storage = agent.storage
                break

        if not storage:
            return MessageListResponse(messages=[], total=0)

        try:
            query = storage.build_select_query(
                collection="astra_messages",
                filter_dict={"thread_id": thread_id},
                sort=[("created_at", 1)],
            )
            rows = await storage.fetch_all(query)

            messages = []
            for row in rows:
                messages.append(
                    MessageResponse(
                        id=row["id"],
                        thread_id=row["thread_id"],
                        role=row.get("role", "user"),
                        content=row.get("content", ""),
                        created_at=_parse_datetime(row.get("created_at")),
                        metadata=row.get("metadata"),
                    )
                )

            return MessageListResponse(messages=messages, total=len(messages))

        except Exception as e:
            logger.error(f"Error listing messages: {e}")
            return MessageListResponse(messages=[], total=0)

    @router.post(
        "/{thread_id}/messages",
        response_model=MessageResponse,
        summary="Add message",
        description="Add a message to a thread",
    )
    async def add_message(
        thread_id: str,
        request: AddMessageRequest,
    ) -> MessageResponse:
        """Add a message to a thread."""
        # Validate role
        valid_roles = {"user", "assistant", "system", "tool"}
        if request.role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role '{request.role}'. Must be one of: {valid_roles}",
            )

        storage = None
        for agent in registry.agents.values():
            if hasattr(agent, "storage") and agent.storage:
                storage = agent.storage
                break

        if not storage:
            raise HTTPException(status_code=400, detail="No storage configured")

        now = datetime.now(timezone.utc)
        message_id = str(uuid.uuid4())

        try:
            # Get next sequence
            sequence = await storage.messages.get_next_sequence(thread_id)

            # Insert message
            message_data = {
                "id": message_id,
                "thread_id": thread_id,
                "role": request.role,
                "content": request.content,
                "sequence": sequence,
                "created_at": now,
                "metadata": request.metadata,
            }

            query = storage.build_insert_query(collection="astra_messages", data=message_data)
            await storage.execute(query)

            # Update thread updated_at
            update_query = storage.build_update_query(
                collection="astra_threads",
                filter_dict={"id": thread_id},
                update_data={"updated_at": now},
            )
            await storage.execute(update_query)

            return MessageResponse(
                id=message_id,
                thread_id=thread_id,
                role=request.role,
                content=request.content,
                created_at=now,
                metadata=request.metadata,
            )

        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to add message: {e!s}")

    @router.delete(
        "/{thread_id}/messages",
        summary="Clear messages",
        description="Delete all messages in a thread",
    )
    async def clear_messages(thread_id: str) -> dict[str, str]:
        """Clear all messages in a thread."""
        storage = None
        for agent in registry.agents.values():
            if hasattr(agent, "storage") and agent.storage:
                storage = agent.storage
                break

        if not storage:
            raise HTTPException(status_code=400, detail="No storage configured")

        try:
            query = storage.build_delete_query(
                collection="astra_messages",
                filter_dict={"thread_id": thread_id},
            )
            await storage.execute(query)

            return {"message": f"Messages cleared from thread '{thread_id}'"}

        except Exception as e:
            logger.error(f"Error clearing messages: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to clear messages: {e!s}")

    return router


def _parse_datetime(value: Any) -> datetime:
    """Parse datetime from various formats."""
    if value is None:
        return datetime.utcnow()

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()

    return datetime.utcnow()
