# Astra MemoryBase Package

A lightweight, modular memory storage and retrieval system for AI agents. Provides persistent context through semantic search, metadata filtering, and optional vector embeddings.

## Features

### 🧠 Core Capabilities

- **Memory Storage**: Store text content with optional embeddings and metadata
- **Semantic Search**: Find relevant memories using keyword matching (vector search coming soon)
- **Metadata Filtering**: Filter memories by user, source, or custom metadata
- **Caching**: LRU cache for fast repeated queries
- **Observability**: Automatic tracing and metrics integration

### 🏗️ Architecture

- **Composition Pattern**: Clean separation of concerns
- **Pluggable Backends**: Easy to switch from in-memory to Qdrant/Redis/Pinecone
- **Async-First**: Non-blocking operations throughout
- **MVP-Ready**: In-memory store works out of the box

## Quick Start

### Installation

```bash
cd packages/memorybase
pip install -e .
```

### Basic Usage

```python
import asyncio
from memorybase import MemoryClient, MemoryEntry

async def main():
    # Initialize client (uses in-memory store by default)
    client = MemoryClient()

    # Create memory entries
    entries = [
        MemoryEntry(
            id="mem-1",
            project_id="project-123",
            content="User prefers dark mode UI and large fonts",
            metadata={"source": "user_preference", "category": "ui"}
        ),
        MemoryEntry(
            id="mem-2",
            project_id="project-123",
            content="User mentioned they work best in the morning",
            metadata={"source": "conversation", "category": "schedule"}
        )
    ]

    # Add memories
    ids = await client.add(entries)
    print(f"Added {len(ids)} memories: {ids}")

    # Search memories
    results = await client.search(
        project_id="project-123",
        query="UI preferences",
        top_k=3
    )

    print(f"\nFound {len(results)} results:")
    for result in results:
        print(f"  - {result.entry.content} (score: {result.score:.2f})")

    # Get count
    count = await client.count("project-123")
    print(f"\nTotal memories in project: {count}")

asyncio.run(main())
```

## Architecture

### Components

```
memorybase/
├── client.py              # MemoryClient - main interface
├── models.py              # MemoryEntry, SearchResult data models
├── base_store.py          # BaseMemoryStore abstract interface
├── store_inmemory.py      # InMemoryStore implementation (MVP)
└── cache.py               # MemoryCache for search result caching
```

### Data Model

**MemoryEntry** - Represents a single memory:

- `id`: Unique identifier
- `project_id`: Project/namespace identifier
- `content`: Text content
- `embedding`: Optional vector embedding (for future semantic search)
- `metadata`: Optional key-value metadata for filtering
- `user_id`: Optional user identifier
- `created_at`: Timestamp

**SearchResult** - Search result with relevance score:

- `entry`: MemoryEntry
- `score`: Relevance score (0.0 to 1.0)

### Storage Backends

#### InMemoryStore (MVP)

- Dictionary-based storage
- Fast keyword matching
- Perfect for development and testing
- Data lost on process restart

#### Future Backends

- **QdrantStore**: Vector database for semantic search
- **RedisStore**: Persistent in-memory store
- **PineconeStore**: Managed vector database

## API Reference

### MemoryClient

Main interface for all memory operations.

#### `add(entries: List[MemoryEntry]) -> List[str]`

Add memory entries to the store.

```python
entries = [MemoryEntry(id="1", project_id="p1", content="Memory text")]
ids = await client.add(entries)
```

#### `search(project_id: str, query: str, top_k: int = 5, filters: Optional[dict] = None) -> List[SearchResult]`

Search for relevant memories.

```python
results = await client.search(
    project_id="project-123",
    query="user preferences",
    top_k=5,
    filters={"user_id": "user-456"}
)
```

#### `get(entry_id: str) -> Optional[MemoryEntry]`

Retrieve a specific memory by ID.

```python
entry = await client.get("mem-1")
```

#### `delete(entry_ids: List[str]) -> int`

Delete memories by IDs.

```python
deleted = await client.delete(["mem-1", "mem-2"])
```

#### `count(project_id: Optional[str] = None) -> int`

Get total count of memories.

```python
total = await client.count("project-123")
```

### MemoryEntry

Create memory entries with Pydantic validation.

```python
entry = MemoryEntry(
    id="mem-1",
    project_id="project-123",
    content="User prefers dark mode",
    metadata={"source": "conversation"},
    user_id="user-456"
)
```

## Observability Integration

MemoryBase automatically integrates with the Observability layer:

- **Traces**: All operations create spans (`astra.memorybase.add`, `astra.memorybase.search`)
- **Metrics**: Memory usage and operation counts
- **Logs**: Structured logging for all operations

```python
# Observability is automatically used if available
from observability import Observability
obs = Observability.init()

# MemoryClient will automatically use it
client = MemoryClient()  # Uses obs singleton
```

## Caching

Search results are automatically cached with TTL:

```python
# First search - queries store
results1 = await client.search("project-123", "query")

# Second search (same query) - uses cache
results2 = await client.search("project-123", "query")

# Clear cache if needed
client.clear_cache()
```

## Advanced Usage

### Custom Storage Backend

```python
from memorybase import BaseMemoryStore, MemoryClient

class MyCustomStore(BaseMemoryStore):
    async def add(self, entries):
        # Your implementation
        pass

    async def search(self, project_id, query, top_k, filters):
        # Your implementation
        pass

    # ... implement other methods

# Use custom store
client = MemoryClient(store=MyCustomStore())
```

### Custom Cache

```python
from memorybase import MemoryCache, MemoryClient

cache = MemoryCache(max_size=500, ttl_seconds=600)
client = MemoryClient(cache=cache)
```

### With Observability

```python
from observability import Observability
from memorybase import MemoryClient

obs = Observability.init()
client = MemoryClient(observability=obs)

# All operations are automatically traced
await client.add([...])
```

## Performance Characteristics

- **Add Operation**: O(1) per entry
- **Search Operation**: O(n) for keyword matching (n = entries in project)
- **Cache Hit**: O(1) lookup
- **Memory Usage**: ~1KB per entry (without embeddings)

## Future Enhancements

- [ ] Vector similarity search with embeddings
- [ ] Qdrant backend integration
- [ ] Redis backend for persistence
- [ ] Batch operations for bulk adds
- [ ] Memory summarization
- [ ] TTL-based expiration for entries
- [ ] Full-text search improvements

## Testing

```python
import asyncio
from memorybase import MemoryClient, MemoryEntry

async def test_memory():
    client = MemoryClient()

    # Test add
    entries = [MemoryEntry(id="1", project_id="p1", content="test")]
    ids = await client.add(entries)
    assert len(ids) == 1

    # Test search
    results = await client.search("p1", "test")
    assert len(results) > 0

    # Test get
    entry = await client.get(ids[0])
    assert entry is not None

    print("All tests passed!")

asyncio.run(test_memory())
```

## Dependencies

- `pydantic>=2.0.0`: Data validation and models
- `observability` (optional): Tracing and metrics

## License

Part of the Astra AI platform.
