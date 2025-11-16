"""
MemoryBase package for Astra.

Provides memory storage and retrieval capabilities for AI agents,
with support for vector embeddings, metadata filtering, and semantic search.

Main Components:
- MemoryClient: Primary interface for memory operations
- MemoryEntry: Data model for memory entries
- BaseMemoryStore: Abstract interface for storage backends
- InMemoryStore: In-memory implementation (MVP)
- MemoryCache: LRU cache for search results

Usage:
    from memorybase import MemoryClient, MemoryEntry
    
    # Initialize client (uses in-memory store by default)
    client = MemoryClient()
    
    # Add memories
    entries = [
        MemoryEntry(
            id="mem-1",
            project_id="project-123",
            content="User prefers dark mode UI",
            metadata={"source": "user_preference"}
        )
    ]
    await client.add(entries)
    
    # Search memories
    results = await client.search("project-123", "UI preferences", top_k=5)
    for result in results:
        print(f"{result.entry.content} (score: {result.score})")
"""

from .client import MemoryClient
from .models import MemoryEntry, SearchResult
from .base_store import BaseMemoryStore
from .store_inmemory import InMemoryStore
from .cache import MemoryCache

# Version info
__version__ = "0.1.0"
__author__ = "Himanshu Sharma"
__email__ = "himanshu.kumarr07@gmail.com"

# Main exports
__all__ = [
    # Main client
    "MemoryClient",
    
    # Data models
    "MemoryEntry",
    "SearchResult",
    
    # Storage interfaces
    "BaseMemoryStore",
    "InMemoryStore",
    
    # Cache
    "MemoryCache",
    
    # Metadata
    "__version__",
    "__author__",
    "__email__",
]
