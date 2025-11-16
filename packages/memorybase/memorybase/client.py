"""
MemoryClient - Main interface for MemoryBase layer.

Provides a clean facade for memory operations with observability integration,
caching, and error handling. This is the primary interface used by the framework layer.
"""

import hashlib
from typing import Any, List, Optional

try:
    from opentelemetry.trace import Status, StatusCode
except ImportError:
    # OpenTelemetry not available - observability will handle this
    Status = None
    StatusCode = None

from .base_store import BaseMemoryStore
from .cache import MemoryCache
from .models import MemoryEntry, SearchResult
from .store_inmemory import InMemoryStore


class MemoryClient:
    """
    Main client interface for MemoryBase operations.
    
    Provides a clean API for memory storage and retrieval with:
    - Automatic caching of search results
    - Observability integration (tracing, metrics, logging)
    - Error handling and validation
    - Easy backend switching (in-memory, Qdrant, etc.)
    
    Usage:
        from memorybase import MemoryClient
        
        client = MemoryClient()
        await client.add([MemoryEntry(...)])
        results = await client.search("project-123", "query text")
    """
    
    def __init__(
        self,
        store: Optional[BaseMemoryStore] = None,
        cache: Optional[MemoryCache] = None,
        observability: Optional[Any] = None
    ):
        """
        Initialize the memory client.
        
        Args:
            store: Storage backend (defaults to InMemoryStore)
            cache: Cache instance (defaults to MemoryCache with defaults)
            observability: Observability instance (optional, will try to get singleton)
        """
        self.store = store or InMemoryStore()
        self.cache = cache or MemoryCache()
        
        # Try to get observability instance if not provided
        self.obs = observability
        if self.obs is None:
            try:
                from observability import Observability
                self.obs = Observability.get_instance()
            except (RuntimeError, ImportError):
                # Observability not available - continue without it
                self.obs = None
    
    async def add(self, entries: List[MemoryEntry]) -> List[str]:
        """
        Add memory entries to the store.
        
        Automatically traces the operation and records metrics.
        
        Args:
            entries: List of memory entries to add
            
        Returns:
            List of IDs for the added entries
            
        Raises:
            ValueError: If entries are invalid
            RuntimeError: If storage operation fails
        """
        if not entries:
            return []
        
        # Use context manager for proper span lifecycle
        if self.obs:
            with self.obs.tracer.get_tracer().start_as_current_span(
                "astra.memorybase.add"
            ) as span:
                # Set span attributes
                span.set_attribute("entries_count", len(entries))
                project_ids = list(set(e.project_id for e in entries))
                span.set_attribute("project_ids", str(project_ids))
                
                try:
                    # Validate entries
                    for entry in entries:
                        if not entry.content:
                            raise ValueError(f"Entry {entry.id} has empty content")
                        if not entry.project_id:
                            raise ValueError(f"Entry {entry.id} missing project_id")
                    
                    # Add to store
                    ids = await self.store.add(entries)
                    
                    # Log operation
                    self.obs.logger.info(
                        f"Added {len(ids)} memory entries",
                        entries_count=len(ids),
                        project_ids=project_ids
                    )
                    
                    # Set span status to OK
                    if Status and StatusCode:
                        span.set_status(Status(StatusCode.OK))
                    
                    return ids
                    
                except Exception as e:
                    # Record exception and set error status
                    span.record_exception(e)
                    if Status and StatusCode:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    self.obs.logger.error(
                        "Failed to add memory entries",
                        exception=e,
                        entries_count=len(entries)
                    )
                    raise
        else:
            # No observability - just execute
            for entry in entries:
                if not entry.content:
                    raise ValueError(f"Entry {entry.id} has empty content")
                if not entry.project_id:
                    raise ValueError(f"Entry {entry.id} missing project_id")
            
            return await self.store.add(entries)
    
    async def search(
        self,
        project_id: str,
        query: str,
        top_k: int = 5,
        filters: Optional[dict] = None,
        use_cache: bool = True
    ) -> List[SearchResult]:
        """
        Search for relevant memory entries.
        
        Checks cache first, then queries the store. Results are cached
        for future queries.
        
        Args:
            project_id: Project/namespace to search within
            query: Search query text
            top_k: Maximum number of results to return
            filters: Optional metadata filters
            use_cache: Whether to use cache (default: True)
            
        Returns:
            List of search results with relevance scores
        """
        if not query or not query.strip():
            return []
        
        # Use context manager for proper span lifecycle
        if self.obs:
            with self.obs.tracer.get_tracer().start_as_current_span(
                "astra.memorybase.search"
            ) as span:
                # Set span attributes
                span.set_attribute("project_id", project_id)
                span.set_attribute("query_length", len(query))
                span.set_attribute("top_k", top_k)
                if filters:
                    span.set_attribute("has_filters", True)
                
                try:
                    # Check cache first
                    cache_key = None
                    if use_cache:
                        cache_key = self._make_cache_key(project_id, query, filters)
                        cached = self.cache.get(cache_key)
                        if cached is not None:
                            span.set_attribute("cache_hit", True)
                            self.obs.logger.debug(
                                "Memory search cache hit",
                                project_id=project_id,
                                query=query[:50]  # Truncate for logging
                            )
                            if Status and StatusCode:
                                span.set_status(Status(StatusCode.OK))
                            return cached
                    
                    span.set_attribute("cache_hit", False)
                    
                    # Query store
                    results = await self.store.search(
                        project_id=project_id,
                        query=query,
                        top_k=top_k,
                        filters=filters
                    )
                    
                    # Cache results
                    if use_cache and cache_key:
                        self.cache.set(cache_key, results)
                    
                    # Log operation
                    self.obs.logger.info(
                        f"Memory search completed: {len(results)} results",
                        project_id=project_id,
                        results_count=len(results),
                        query=query[:50]
                    )
                    
                    # Set span attributes for results
                    span.set_attribute("results_count", len(results))
                    
                    # Set span status to OK
                    if Status and StatusCode:
                        span.set_status(Status(StatusCode.OK))
                    
                    return results
                    
                except Exception as e:
                    # Record exception and set error status
                    span.record_exception(e)
                    if Status and StatusCode:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    self.obs.logger.error(
                        "Memory search failed",
                        exception=e,
                        project_id=project_id,
                        query=query[:50]
                    )
                    raise
        else:
            # No observability - just execute
            # Check cache first
            cache_key = None
            if use_cache:
                cache_key = self._make_cache_key(project_id, query, filters)
                cached = self.cache.get(cache_key)
                if cached is not None:
                    return cached
            
            # Query store
            results = await self.store.search(
                project_id=project_id,
                query=query,
                top_k=top_k,
                filters=filters
            )
            
            # Cache results
            if use_cache and cache_key:
                self.cache.set(cache_key, results)
            
            return results
    
    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve a specific memory entry by ID.
        
        Args:
            entry_id: Unique identifier of the entry
            
        Returns:
            Memory entry if found, None otherwise
        """
        if self.obs:
            with self.obs.tracer.get_tracer().start_as_current_span(
                "astra.memorybase.get"
            ) as span:
                span.set_attribute("entry_id", entry_id)
                try:
                    result = await self.store.get(entry_id)
                    if Status and StatusCode:
                        span.set_status(Status(StatusCode.OK))
                    span.set_attribute("found", result is not None)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    if Status and StatusCode:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        return await self.store.get(entry_id)
    
    async def delete(self, entry_ids: List[str]) -> int:
        """
        Delete memory entries by IDs.
        
        Args:
            entry_ids: List of entry IDs to delete
            
        Returns:
            Number of entries successfully deleted
        """
        if not entry_ids:
            return 0
        
        if self.obs:
            with self.obs.tracer.get_tracer().start_as_current_span(
                "astra.memorybase.delete"
            ) as span:
                span.set_attribute("entry_ids_count", len(entry_ids))
                try:
                    deleted = await self.store.delete(entry_ids)
                    self.obs.logger.info(
                        f"Deleted {deleted} memory entries",
                        deleted_count=deleted
                    )
                    span.set_attribute("deleted_count", deleted)
                    if Status and StatusCode:
                        span.set_status(Status(StatusCode.OK))
                    return deleted
                except Exception as e:
                    span.record_exception(e)
                    if Status and StatusCode:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        
        return await self.store.delete(entry_ids)
    
    async def count(self, project_id: Optional[str] = None) -> int:
        """
        Get the total count of memory entries.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            Total number of entries
        """
        return await self.store.count(project_id)
    
    async def health_check(self) -> bool:
        """
        Check if the memory store is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return await self.store.health_check()
    
    def _make_cache_key(self, project_id: str, query: str, filters: Optional[dict] = None) -> str:
        """
        Generate a cache key for a search query.
        
        Args:
            project_id: Project identifier
            query: Search query
            filters: Optional filters
            
        Returns:
            Cache key string
        """
        key_parts = [project_id, query]
        if filters:
            # Sort filters for consistent key generation
            sorted_filters = sorted(filters.items())
            key_parts.append(str(sorted_filters))
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def clear_cache(self) -> None:
        """
        Clear the search result cache.
        
        Useful for testing or when you want to force fresh queries.
        """
        self.cache.clear()
        if self.obs:
            self.obs.logger.info("Memory cache cleared")
