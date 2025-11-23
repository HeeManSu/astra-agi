from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator

class Thread(BaseModel):
    """Represents a conversation thread."""
    id: str
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Message(BaseModel):
    """Represents a single message in a thread."""
    id: str
    thread_id: str
    role: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {'user', 'assistant', 'system', 'tool'}
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v
