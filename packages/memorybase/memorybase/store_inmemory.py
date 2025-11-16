"""
In-memory storage implementation for MemoryBase.

A simple dictionary-based store for MVP, ideal for local development,
testing, and first agent deployments. All data is stored in process memory.
"""

import uuid
from typing import Dict, List, Optional

from .base_store import BaseMemoryStore
from .models import MemoryEntry, SearchResult


class InMemoryStore(BaseMemoryStore):
    """
    In-memory storage implementation using dictionaries.
    
    Stores all memory entries in process memory. Data is lost on process restart.
    Suitable for MVP, testing, and development environments.
    
    Features:
    - Fast lookups by ID
    - Simple text-based search (keyword matching)
    - Optional vector similarity search (if embeddings provided)
    - Metadata filtering
    """
    
    def __init__(self):
        """
        Initialize the in-memory store.
        
        Creates empty dictionaries for entries and embeddings.
        """
        self._store: Dict[str, MemoryEntry] = {}
        self._embeddings: Dict[str, List[float]] = {}
        self._project_index: Dict[str, List[str]] = {}  # project_id -> [entry_ids]
    
    async def add(self, entries: List[MemoryEntry]) -> List[str]:
        """
        Add memory entries to the in-memory store.
        
        Args:
            entries: List of memory entries to add
            
        Returns:
            List of IDs for the added entries
        """
        ids = []
        
        for entry in entries:
            # Generate ID if not provided
            if not entry.id:
                entry.id = str(uuid.uuid4())
            
            entry_id = entry.id
            
            # Store the entry
            self._store[entry_id] = entry
            
            # Store embedding if provided
            if entry.embedding:
                self._embeddings[entry_id] = entry.embedding
            
            # Update project index
            if entry.project_id not in self._project_index:
                self._project_index[entry.project_id] = []
            if entry_id not in self._project_index[entry.project_id]:
                self._project_index[entry.project_id].append(entry_id)
            
            ids.append(entry_id)
        
        return ids
    
    async def search(
        self,
        project_id: str,
        query: str,
        top_k: int = 5,
        filters: Optional[dict] = None
    ) -> List[SearchResult]:
        """
        Search for relevant memory entries using text matching.
        
        For MVP, uses simple keyword matching. Future versions can use
        vector similarity if embeddings are available.
        
        Args:
            project_id: Project/namespace to search within
            query: Search query (text)
            top_k: Maximum number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of search results with relevance scores
        """
        # Get entries for this project
        project_entry_ids = self._project_index.get(project_id, [])
        candidates = [
            self._store[entry_id]
            for entry_id in project_entry_ids
            if entry_id in self._store
        ]
        
        # Apply metadata filters if provided
        if filters:
            filtered = []
            for entry in candidates:
                match = True
                for key, value in filters.items():
                    if key == "user_id" and entry.user_id != value:
                        match = False
                        break
                    elif entry.metadata and entry.metadata.get(key) != value:
                        match = False
                        break
                if match:
                    filtered.append(entry)
            candidates = filtered
        
        # Simple text matching (keyword search)
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        results = []
        for entry in candidates:
            content_lower = entry.content.lower()
            content_words = set(content_lower.split())
            
            # Calculate simple relevance score (word overlap)
            if query_words:
                overlap = len(query_words & content_words)
                score = overlap / len(query_words)
            else:
                score = 0.0
            
            # Also check if query is substring of content
            if query_lower in content_lower:
                score = max(score, 0.5)
            
            if score > 0:
                results.append(SearchResult(entry=entry, score=score))
        
        # Sort by score (descending) and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve a specific memory entry by ID.
        
        Args:
            entry_id: Unique identifier of the entry
            
        Returns:
            Memory entry if found, None otherwise
        """
        return self._store.get(entry_id)
    
    async def delete(self, entry_ids: List[str]) -> int:
        """
        Delete memory entries by IDs.
        
        Args:
            entry_ids: List of entry IDs to delete
            
        Returns:
            Number of entries successfully deleted
        """
        deleted = 0
        
        for entry_id in entry_ids:
            if entry_id in self._store:
                entry = self._store[entry_id]
                
                # Remove from project index
                if entry.project_id in self._project_index:
                    if entry_id in self._project_index[entry.project_id]:
                        self._project_index[entry.project_id].remove(entry_id)
                
                # Remove from store and embeddings
                del self._store[entry_id]
                if entry_id in self._embeddings:
                    del self._embeddings[entry_id]
                
                deleted += 1
        
        return deleted
    
    async def count(self, project_id: Optional[str] = None) -> int:
        """
        Get the total count of memory entries.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            Total number of entries
        """
        if project_id:
            return len(self._project_index.get(project_id, []))
        return len(self._store)
    
    async def health_check(self) -> bool:
        """
        Check if the in-memory store is healthy.
        
        Returns:
            Always True for in-memory store
        """
        return True
    
    def clear(self) -> None:
        """
        Clear all stored entries (useful for testing).
        
        Note: This is not part of the base interface but useful for testing.
        """
        self._store.clear()
        self._embeddings.clear()
        self._project_index.clear()
