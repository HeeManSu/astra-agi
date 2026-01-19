"""Thread routes for conversation management."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/threads", tags=["threads"])


class ThreadCreate(BaseModel):
    """Request body for creating a thread."""

    resource_type: str  # "agent" | "team" | "stepper" | "workflow"
    resource_id: str
    resource_name: str
    title: str = ""
    metadata: dict | None = None


class MessageCreate(BaseModel):
    """Request body for adding a message."""

    role: str  # "user" or "assistant"
    content: str


class ThreadResponse(BaseModel):
    """Thread response."""

    id: str
    resource_type: str
    resource_id: str
    resource_name: str
    title: str
    created_at: datetime
    metadata: dict | None = None


class MessageResponse(BaseModel):
    """Message response."""

    id: str
    thread_id: str
    role: str
    content: str
    created_at: datetime


# In-memory storage (replace with database in production)
_threads: dict[str, dict] = {}
_messages: dict[str, list[dict]] = {}


@router.post("/")
async def create_thread(request: ThreadCreate) -> ThreadResponse:
    """Create a new conversation thread."""
    import uuid

    thread_id = str(uuid.uuid4())
    thread = {
        "id": thread_id,
        "resource_type": request.resource_type,
        "resource_id": request.resource_id,
        "resource_name": request.resource_name,
        "title": request.title,
        "created_at": datetime.utcnow(),
        "metadata": request.metadata or {},
    }
    _threads[thread_id] = thread
    _messages[thread_id] = []
    return ThreadResponse(**thread)


@router.get("/{thread_id}")
async def get_thread(thread_id: str) -> ThreadResponse:
    """Get thread details."""
    thread = _threads.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")
    return ThreadResponse(**thread)


@router.get("/{thread_id}/messages")
async def get_messages(thread_id: str) -> list[MessageResponse]:
    """Get all messages in a thread."""
    if thread_id not in _threads:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")
    return [MessageResponse(**msg) for msg in _messages.get(thread_id, [])]


@router.post("/{thread_id}/messages")
async def add_message(thread_id: str, request: MessageCreate) -> MessageResponse:
    """Add a message to a thread."""
    if thread_id not in _threads:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    import uuid

    message = {
        "id": str(uuid.uuid4()),
        "thread_id": thread_id,
        "role": request.role,
        "content": request.content,
        "created_at": datetime.utcnow(),
    }
    _messages[thread_id].append(message)
    return MessageResponse(**message)
