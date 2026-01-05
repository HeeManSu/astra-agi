from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Thread(BaseModel):
    """Represents a conversation thread."""

    id: str
    agent_name: str | None = None
    resource_id: str | None = None
    title: str | None = None
    message_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_archived: bool = False
    deleted_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Message(BaseModel):
    """Represents a single message in a thread."""

    id: str
    thread_id: str
    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    sequence: int = 0
    deleted_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"user", "assistant", "system", "tool"}
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v


class MemoryScope(str, Enum):
    """
    Memory scoping levels for persistent facts.

    Scoping determines who can access and modify facts:

    - USER: User-specific facts (most common)
      Example: "User prefers dark mode", "User's name is John"
      Scoped to: user_id (e.g., "[email protected]")
      Persists: Across all sessions for that user

    - SESSION: Session-specific facts (temporary)
      Example: "Current task: writing report", "Session started at 2pm"
      Scoped to: session_id or thread_id
      Persists: Only within current session/thread

    - AGENT: Agent-specific facts (shared across users)
      Example: "Last maintenance: 2024-01-15", "Agent version: 1.0"
      Scoped to: agent_id
      Persists: Shared by all users of this agent

    - GLOBAL: System-wide facts (shared by all)
      Example: "System version: 1.0.0", "Maintenance window: Sundays"
      Scoped to: None (global)
      Persists: Shared by all agents and users
    """

    USER = "user"  # User-specific facts (e.g., preferences)
    SESSION = "session"  # Session-specific facts (temporary)
    AGENT = "agent"  # Agent-specific facts (shared across users)
    GLOBAL = "global"  # System-wide facts (shared by all)


class Fact(BaseModel):
    """A single persistent fact."""

    id: str
    key: str
    value: Any  # JSON-serializable value
    scope: MemoryScope
    scope_id: str | None = None  # user_id, session_id, agent_id, etc.
    schema_type: str | None = None  # Optional schema name for validation
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    deleted_at: datetime | None = None


class TeamAuth(BaseModel):
    """Team authentication credentials for playground access.

    Single row table - one email/password for the entire team.
    """

    id: str
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None
