"""
Base storage interface for MemoryBase.

Defines the abstract contract that all memory storage backends must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import MemoryEntry, SearchResult


class BaseMemoryStore(ABC):
    """
    Abstract base class for memory storage backends.
    
    All storage implementations (in-memory, Qdrant, Redis, etc.) must
    implement this interface to ensure consistent API across backends.
    """
    
    @abstractmethod
    async def add(self, entries: List[MemoryEntry]) -> List[str]:
        """
        Add memory entries to the store.
        
        Args:
            entries: List of memory entries to add
            
        Returns:
            List of IDs for the added entries
            
        Raises:
            ValueError: If entries are invalid
            RuntimeError: If storage operation fails
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        project_id: str,
        query: str,
        top_k: int = 5,
        filters: Optional[dict] = None
    ) -> List[SearchResult]:
        """
        Search for relevant memory entries.
        
        Args:
            project_id: Project/namespace to search within
            query: Search query (text or will be embedded)
            top_k: Maximum number of results to return
            filters: Optional metadata filters (e.g., {"user_id": "user123"})
            
        Returns:
            List of search results with relevance scores, sorted by score (descending)
        """
        pass
    
    @abstractmethod
    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve a specific memory entry by ID.
        
        Args:
            entry_id: Unique identifier of the entry
            
        Returns:
            Memory entry if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete(self, entry_ids: List[str]) -> int:
        """
        Delete memory entries by IDs.
        
        Args:
            entry_ids: List of entry IDs to delete
            
        Returns:
            Number of entries successfully deleted
        """
        pass
    
    @abstractmethod
    async def count(self, project_id: Optional[str] = None) -> int:
        """
        Get the total count of memory entries.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            Total number of entries
        """
        pass
    
    async def health_check(self) -> bool:
        """
        Check if the storage backend is healthy and accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        return True
