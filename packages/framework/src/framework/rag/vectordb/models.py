"""Core models for RAG operations."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ContentStatus(str, Enum):
    """Content processing status."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Document:
    """Represents a chunk of content with metadata."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str | None = None
    name: str | None = None
    source: str | None = None
    chunk_index: int | None = None
    embedding: list[float] | None = None
    content_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert document to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "name": self.name,
            "source": self.source,
            "chunk_index": self.chunk_index,
            "content_id": self.content_id,
        }


@dataclass
class Content:
    """Represents a content source with lifecycle tracking."""

    id: str
    name: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: ContentStatus = ContentStatus.PROCESSING
    status_message: str | None = None
    content_hash: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_status(self, status: ContentStatus, message: str | None = None) -> None:
        """Update content status."""
        self.status = status
        self.status_message = message
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert content to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "metadata": self.metadata,
            "status": self.status.value,
            "status_message": self.status_message,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
