"""Thread routes for conversation management.

Provides REST API endpoints for managing conversation threads.
Connects to the storage backend via the global registry.
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from runtime.registry import storage_registry


router = APIRouter(prefix="/threads", tags=["threads"])


class ThreadCreate(BaseModel):
    """Request body for creating a thread."""

    resource_type: str  # "agent" | "team" | "stepper" | "workflow"
    resource_id: str
    resource_name: str
    title: str = ""
    metadata: dict | None = None


class ThreadResponse(BaseModel):
    """Thread response."""

    id: str
    resource_type: str
    resource_id: str
    resource_name: str
    title: str
    created_at: datetime
    updated_at: datetime | None = None
    metadata: dict | None = None


class MessageResponse(BaseModel):
    """Message response."""

    id: str
    thread_id: str
    role: str
    content: str
    sequence: int
    created_at: datetime
    metadata: dict | None = None


def get_storage():
    """Get storage client from registry."""
    storage = storage_registry.get_default()
    if storage is None:
        raise HTTPException(
            status_code=503,
            detail="Storage not configured. Please configure storage in AstraServer.",
        )
    return storage


# Type alias for dependency injection (Ruff B008 compliant)
Storage = Annotated[Any, Depends(get_storage)]


@router.get("/")
async def list_threads(
    storage: Storage,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 50,
) -> list[ThreadResponse]:
    """
    List threads, optionally filtered by resource_type and/or resource_id.

    Query params:
        resource_type: Filter by type (agent, team, etc.)
        resource_id: Filter by specific resource
        limit: Max threads to return (default 50)
    """
    threads = await storage.list_threads(
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )

    return [
        ThreadResponse(
            id=t.id,
            resource_type=t.resource_type,
            resource_id=t.resource_id,
            resource_name=t.resource_name,
            title=t.title,
            created_at=t.created_at,
            updated_at=t.updated_at,
            metadata=t.metadata,
        )
        for t in threads
    ]


@router.post("/")
async def create_thread(
    request: ThreadCreate,
    storage: Storage,
) -> ThreadResponse:
    """Create a new conversation thread."""
    thread = await storage.create_thread(
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        resource_name=request.resource_name,
        title=request.title or "New Chat",
        metadata=request.metadata,
    )

    return ThreadResponse(
        id=thread.id,
        resource_type=thread.resource_type,
        resource_id=thread.resource_id,
        resource_name=thread.resource_name,
        title=thread.title,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        metadata=thread.metadata,
    )


@router.get("/{thread_id}")
async def get_thread(
    thread_id: str,
    storage: Storage,
) -> ThreadResponse:
    """Get thread details by ID."""
    thread = await storage.get_thread(thread_id)

    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    return ThreadResponse(
        id=thread.id,
        resource_type=thread.resource_type,
        resource_id=thread.resource_id,
        resource_name=thread.resource_name,
        title=thread.title,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        metadata=thread.metadata,
    )


@router.get("/{thread_id}/messages")
async def get_messages(
    thread_id: str,
    storage: Storage,
    limit: int = 100,
) -> list[MessageResponse]:
    """Get all messages in a thread, ordered by sequence."""
    # Verify thread exists
    thread = await storage.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    messages = await storage.get_history(thread_id, limit=limit)

    return [
        MessageResponse(
            id=msg.id,
            thread_id=msg.thread_id,
            role=msg.role,
            content=msg.content,
            sequence=msg.sequence,
            created_at=msg.created_at,
            metadata=msg.metadata,
        )
        for msg in messages
    ]


@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: str,
    storage: Storage,
) -> dict:
    """Soft delete a thread."""
    thread = await storage.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    await storage.soft_delete_thread(thread_id)

    return {"success": True, "message": f"Thread '{thread_id}' deleted"}
