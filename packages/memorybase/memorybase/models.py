"""
Data models for MemoryBase layer.

Defines the core data structures for memory storage and retrieval.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """
    Represents a single memory entry in the memory base.
    
    A memory entry contains text content, optional embeddings for semantic search,
    and metadata for filtering and organization.
    """
    
    id: str = Field(..., description="Unique identifier for the memory entry")
    project_id: str = Field(..., description="Project/namespace identifier")
    content: str = Field(..., description="Text content of the memory")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for filtering")
    user_id: Optional[str] = Field(None, description="User identifier (optional)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        frozen = False  # Allow updates if needed


class SearchResult(BaseModel):
    """
    Represents a search result with relevance score.
    
    Used when returning search results with similarity scores.
    """
    
    entry: MemoryEntry
    score: float = Field(..., description="Relevance score (0.0 to 1.0)")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
