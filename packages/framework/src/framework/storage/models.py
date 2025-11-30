from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Thread(BaseModel):
    """Represents a conversation thread."""

    id: str
    resource_id: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_archived: bool = False
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"user", "assistant", "system", "tool"}
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v
