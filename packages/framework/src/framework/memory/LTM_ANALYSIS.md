# Long-Term Memory (LTM) Analysis & Comparison

## Executive Summary

This document analyzes Astra's current Long-Term Memory (LTM) implementation, compares it with Agno and Mastra, and identifies critical features needed for an industry-ready LTM system.

**Status**: Astra has storage infrastructure but lacks dedicated LTM features  
**Goal**: Identify gaps and prioritize features for Persistent Facts (Tier 2) implementation

---

## What is Long-Term Memory (LTM)?

LTM enables AI agents to:

- **Persist information** across sessions and conversations
- **Recall user preferences** and learned facts
- **Build knowledge** over time through interactions
- **Personalize responses** based on historical context

Unlike Short-Term Memory (STM) which maintains immediate conversation context, LTM stores information that persists beyond a single session.

---

## Current State: Astra

### ✅ What Astra Has

#### 1. **Storage Infrastructure** (`packages/framework/src/framework/storage/`)

**Strengths:**

- ✅ **Database-agnostic abstraction** (`StorageBackend`)
- ✅ **Multiple backends**: LibSQL/SQLite, MongoDB
- ✅ **Async-first design** (all operations are async)
- ✅ **Queue-based batching** (`SaveQueueManager`) for performance
- ✅ **Soft delete support** (deleted_at timestamps)
- ✅ **Clean domain stores**: `ThreadStore`, `MessageStore`
- ✅ **Query builders** for database-agnostic operations

**Current Capabilities:**

```python
# Thread management
await storage.create_thread(thread_id, title, metadata)
await storage.get_thread(thread_id)
await storage.soft_delete_thread(thread_id)

# Message persistence
await storage.add_message(thread_id, role, content, tool_calls, metadata)
await storage.get_history(thread_id, limit)
await storage.soft_delete_message(message_id)
```

**What's Missing for LTM:**

- ❌ No dedicated fact/preference storage
- ❌ No scoped memory (user/session/agent/global)
- ❌ No fact extraction from conversations
- ❌ No fact search/retrieval by key or query
- ❌ No fact update/merge logic
- ❌ No structured fact schemas

#### 2. **KnowledgeBase (RAG for Documents)**

**Location**: `packages/framework/src/framework/KnowledgeBase/`

**Capabilities:**

- ✅ Vector storage (LanceDB)
- ✅ Embedders (HuggingFace, OpenAI)
- ✅ Document chunking and indexing
- ✅ Semantic search

**Note**: This is for **document RAG**, not conversation memory. However, infrastructure can be reused for Semantic Memory (Tier 3).

---

## Comparison: Agno vs Mastra vs Astra

### Agno's LTM Features

#### 1. **Storage & Memory Classes**

- **`Storage`**: Long-term persistent storage
- **`Memory`**: Session-based memory
- Built-in integration with agents

#### 2. **User Memories**

- Store user preferences and facts
- Persist across sessions
- Accessible via agent context

#### 3. **Advanced Context Management**

- Session history
- User memories
- Chat history
- Dynamic context
- Few-shot examples

#### 4. **Agentic RAG**

- Search across 20+ vector databases
- Runtime information retrieval
- Semantic search capabilities

**Key Features:**

- ✅ Structured memory classes
- ✅ User-scoped persistence
- ✅ Context management
- ✅ Vector search integration

**Missing in Astra:**

- ❌ No dedicated `Storage`/`Memory` classes for facts
- ❌ No user-scoped memory
- ❌ No fact extraction/management

---

### Mastra's LTM Features

#### 1. **Persistent Agent Memory**

- Agents remember past interactions
- User preferences storage
- Important facts persistence
- Personalized conversations

#### 2. **Memory & RAG Integration**

- Long-term memory persistence
- SaaS data source synchronization
- Vector-backed retrieval
- Context-aware responses

#### 3. **Durable Workflows**

- Graph-based state machines
- Built-in tracing
- Reliable operation sequences

**Key Features:**

- ✅ Persistent memory for agents
- ✅ User preference storage
- ✅ RAG integration
- ✅ Workflow state persistence

**Missing in Astra:**

- ❌ No persistent fact storage
- ❌ No preference management
- ❌ No workflow state memory

---

## Critical Features for Industry-Ready LTM

Based on the comparison, here are the **essential features** needed for Astra's LTM:

### Tier 1: Core LTM Features (Must Have)

#### 1. **Persistent Facts Storage**

```python
class PersistentFacts:
    """Long-term declarative memory for facts and preferences."""

    # CRUD Operations
    async def add(key: str, value: Any, scope: MemoryScope) -> None
    async def get(key: str, scope: MemoryScope) -> Any | None
    async def update(key: str, value: Any) -> None
    async def delete(key: str, scope: MemoryScope) -> None

    # Search & Retrieval
    async def search(query: str, scope: MemoryScope) -> list[Fact]
    async def get_all(scope: MemoryScope) -> list[Fact]

    # Fact Extraction
    async def extract_from_messages(messages: list) -> list[Fact]
```

**Why Critical:**

- Enables user preference storage ("User prefers dark mode")
- Stores learned facts ("User's timezone is IST")
- Persists agent state ("Last completed task: product launch")
- Foundation for personalization

#### 2. **Memory Scoping**

```python
class MemoryScope(Enum):
    USER = "user"        # User-specific (e.g., preferences)
    SESSION = "session"  # Session-specific (temporary)
    AGENT = "agent"      # Agent-specific (shared across users)
    GLOBAL = "global"   # System-wide (shared by all)
```

**Why Critical:**

- Multi-user support (isolate user data)
- Session isolation (temporary vs persistent)
- Agent-level memory (shared knowledge)
- Enterprise multi-tenancy foundation

#### 3. **Fact Extraction**

```python
async def extract_from_messages(messages: list[dict]) -> list[Fact]:
    """LLM-based extraction of facts from conversation."""
    # Use LLM to identify facts like:
    # - "User's name is Himanshu"
    # - "User prefers concise responses"
    # - "User's company is XYZ"
```

**Why Critical:**

- Automatic learning from conversations
- No manual fact entry required
- Reduces developer burden
- Enables continuous learning

#### 4. **Intelligent Updates**

```python
class FactUpdate:
    ADD = "add"      # New fact detected
    UPDATE = "update"  # Existing fact modified
    DELETE = "delete"  # Contradicting information
    NOOP = "noop"    # No change needed
```

**Why Critical:**

- Handles contradictions intelligently
- Merges related facts
- Prevents duplicate storage
- Maintains data consistency

---

### Tier 2: Enhanced Features (Should Have)

#### 5. **Structured Fact Schemas**

```python
class UserPreferences(BaseModel):
    theme: str = "light"
    timezone: str = "UTC"
    language: str = "en"

# Store with schema validation
await facts.add("user_prefs", UserPreferences(...), scope=MemoryScope.USER)
```

**Why Important:**

- Type safety
- Validation
- Better developer experience
- Schema evolution support

#### 6. **Fact Search & Filtering**

```python
# Search by keyword
facts = await facts.search("timezone", scope=MemoryScope.USER)

# Filter by metadata
facts = await facts.filter(
    scope=MemoryScope.USER,
    tags=["preference", "ui"],
    created_after=datetime(2024, 1, 1)
)
```

**Why Important:**

- Efficient retrieval
- Metadata-based queries
- Tag-based organization
- Temporal queries

#### 7. **Fact Deduplication**

```python
async def deduplicate(self) -> None:
    """Merge duplicate facts, resolve conflicts."""
    # Identify similar facts
    # Merge or resolve conflicts
    # Update references
```

**Why Important:**

- Prevents data bloat
- Maintains consistency
- Reduces storage costs
- Improves retrieval accuracy

---

### Tier 3: Advanced Features (Nice to Have)

#### 8. **Fact Versioning**

- Track fact changes over time
- Rollback to previous versions
- Audit trail

#### 9. **Fact Relationships**

- Link related facts
- Build knowledge graphs
- Traverse relationships

#### 10. **Fact Expiration**

- TTL for temporary facts
- Auto-cleanup of stale data
- Time-based relevance

---

## Storage Backend Requirements

### Current Support

- ✅ **LibSQL/SQLite**: Good for development, single-user
- ✅ **MongoDB**: Good for production, multi-user

### Needed for LTM

- ✅ **PostgreSQL**: Enterprise standard, better for complex queries
- ✅ **Redis**: Optional, for high-performance caching
- ✅ **JSON columns**: For flexible fact schemas

### Storage Schema Proposal

```sql
CREATE TABLE astra_facts (
    id VARCHAR(64) PRIMARY KEY,
    key VARCHAR(255) NOT NULL,
    value JSON NOT NULL,
    scope VARCHAR(32) NOT NULL,  -- user, session, agent, global
    scope_id VARCHAR(64),        -- user_id, session_id, agent_id
    schema_type VARCHAR(128),    -- Optional schema name
    tags TEXT[],                 -- Array of tags
    metadata JSON,               -- Additional metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,        -- Optional expiration
    deleted_at TIMESTAMP,        -- Soft delete

    INDEX idx_facts_key_scope (key, scope, scope_id),
    INDEX idx_facts_scope (scope, scope_id),
    INDEX idx_facts_tags (tags),
    INDEX idx_facts_created (created_at)
);
```

---

## Implementation Priority

### Phase 1: Core LTM (MVP)

1. ✅ **Persistent Facts Storage** - CRUD operations
2. ✅ **Memory Scoping** - USER, SESSION, AGENT, GLOBAL
3. ✅ **Basic Fact Extraction** - LLM-based extraction
4. ✅ **Storage Integration** - Use existing `StorageBackend`

### Phase 2: Enhanced Features

5. ✅ **Structured Schemas** - Pydantic schema support
6. ✅ **Fact Search** - Keyword and metadata search
7. ✅ **Intelligent Updates** - ADD/UPDATE/DELETE/NOOP logic

### Phase 3: Advanced Features

8. ✅ **Fact Deduplication** - Merge and conflict resolution
9. ✅ **Fact Versioning** - Change tracking
10. ✅ **Fact Relationships** - Knowledge graphs

---

## Comparison Matrix

| Feature                    | Astra (Current) | Agno | Mastra | Priority   |
| -------------------------- | --------------- | ---- | ------ | ---------- |
| **Storage Infrastructure** | ✅              | ✅   | ✅     | -          |
| **Persistent Facts**       | ❌              | ✅   | ✅     | **HIGH**   |
| **Memory Scoping**         | ❌              | ✅   | ✅     | **HIGH**   |
| **Fact Extraction**        | ❌              | ✅   | ⚠️     | **HIGH**   |
| **Fact Search**            | ❌              | ✅   | ✅     | **MEDIUM** |
| **Structured Schemas**     | ❌              | ⚠️   | ⚠️     | **MEDIUM** |
| **Intelligent Updates**    | ❌              | ⚠️   | ⚠️     | **MEDIUM** |
| **Fact Deduplication**     | ❌              | ❌   | ❌     | **LOW**    |
| **Fact Versioning**        | ❌              | ❌   | ❌     | **LOW**    |
| **Vector Search**          | ✅ (RAG)        | ✅   | ✅     | -          |

**Legend:**

- ✅ Fully implemented
- ⚠️ Partially implemented
- ❌ Not implemented

---

## Key Takeaways

### What Astra Has (Advantages)

1. ✅ **Clean storage abstraction** - Database-agnostic design
2. ✅ **Async-first** - Better performance
3. ✅ **Queue-based batching** - Efficient writes
4. ✅ **Soft delete support** - Data safety
5. ✅ **Vector infrastructure** - Can reuse for Semantic Memory

### What Astra Needs (Gaps)

1. ❌ **Dedicated LTM layer** - No PersistentFacts class
2. ❌ **Memory scoping** - No USER/SESSION/AGENT/GLOBAL scopes
3. ❌ **Fact extraction** - No LLM-based extraction
4. ❌ **Fact management** - No CRUD for facts/preferences
5. ❌ **Search capabilities** - No fact search/retrieval

### Industry Standards (Agno/Mastra)

- Both have dedicated memory classes
- Both support user-scoped persistence
- Both integrate with agents seamlessly
- Both enable personalization

---

## Recommendations

### Immediate Actions (Phase 1)

1. **Create `PersistentFacts` class** - Core LTM functionality
2. **Implement memory scoping** - USER, SESSION, AGENT, GLOBAL
3. **Add fact extraction** - LLM-based from conversations
4. **Integrate with Agent** - Seamless fact access in agents

### Next Steps (Phase 2)

5. **Add structured schemas** - Pydantic validation
6. **Implement fact search** - Keyword and metadata queries
7. **Add intelligent updates** - Conflict resolution

### Future Enhancements (Phase 3)

8. **Fact deduplication** - Merge similar facts
9. **Fact versioning** - Change tracking
10. **Fact relationships** - Knowledge graphs

---

## Low-Level Design (LLD): Persistent Facts Implementation

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Layer                           │
│  Agent(enable_persistent_facts=True)                    │
│  or                                                      │
│  Agent(persistent_facts=PersistentFacts(...))           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              PersistentFacts Layer                       │
│  - Fact CRUD (add/get/update/delete)                   │
│  - Memory Scoping (USER/SESSION/AGENT/GLOBAL)          │
│  - Fact Extraction (LLM-based)                         │
│  - Fact Search (keyword/metadata)                      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Storage Layer (Existing)                   │
│  - StorageBackend (LibSQL, MongoDB, etc.)              │
│  - FactStore (new domain store)                        │
└─────────────────────────────────────────────────────────┘
```

---

### 1. Initialization Patterns

#### Pattern A: Simple Initialization (Default - Recommended)

```python
from framework.agents import Agent
from framework.storage.databases.libsql import LibSQLStorage

# Setup storage (existing pattern)
storage = LibSQLStorage(url="sqlite+aiosqlite:///./astra.db")
await storage.connect()

# Initialize Agent with persistent facts - that's it!
agent = Agent(
    name="PersonalAssistant",
    instructions="You are a helpful assistant.",
    model=model,
    storage=storage,
    enable_persistent_facts=True,  # Simple flag - uses existing storage
)

# Agent automatically:
# - Creates PersistentFacts instance using Agent.storage
# - Enables automatic fact extraction
# - Uses USER scope by default
# - No extra dependencies or configuration needed
```

**Why this is Astra-specific:**

- Uses `Agent.storage` directly - no separate storage parameter
- Minimal configuration - just one flag
- Follows existing Agent initialization pattern
- Works with any StorageBackend (LibSQL, MongoDB, etc.)

#### Pattern B: Explicit Configuration (Advanced)

```python
from framework.agents import Agent
from framework.memory import PersistentFacts, MemoryScope

# Create PersistentFacts with custom config
persistent_facts = PersistentFacts(
    storage=storage,  # Uses existing storage
    scope=MemoryScope.USER,  # or SESSION, AGENT, GLOBAL
    auto_extract=True,  # Enable automatic extraction
    extraction_model=None,  # Uses agent's model if None
    extraction_template=None,  # Uses default template if None
)

# Initialize Agent with explicit PersistentFacts
agent = Agent(
    name="PersonalAssistant",
    instructions="You are a helpful assistant.",
    model=model,
    storage=storage,
    persistent_facts=persistent_facts,  # Explicit instance
)
```

**When to use:**

- Need custom extraction template
- Want different scope than USER
- Need explicit control over extraction model

---

### 2. Memory Scoping Examples

#### USER Scope (Default - Most Common)

```python
# User-specific facts persist across all sessions
agent = Agent(
    storage=storage,
    enable_persistent_facts=True,  # Defaults to USER scope
)

# User shares information
await agent.invoke(
    "My name is John and I prefer dark mode",
    user_id="[email protected]",  # Scoped to this user
    thread_id="thread_1"
)

# Later, in a different thread
await agent.invoke(
    "What are my preferences?",
    user_id="[email protected]",  # Same user
    thread_id="thread_2"  # Different thread
)
# Agent recalls: "You prefer dark mode" (persisted across threads)
```

#### SESSION Scope (Temporary)

```python
persistent_facts = PersistentFacts(
    storage=storage,
    scope=MemoryScope.SESSION,  # Only persists within session
)

agent = Agent(
    storage=storage,
    persistent_facts=persistent_facts,
)

# Facts stored in this session
await agent.invoke("I'm working on project X", thread_id="session_1")

# Facts cleared when session ends
# Useful for temporary context
```

#### AGENT Scope (Shared Across Users)

```python
persistent_facts = PersistentFacts(
    storage=storage,
    scope=MemoryScope.AGENT,  # Shared by all users of this agent
)

agent = Agent(
    storage=storage,
    persistent_facts=persistent_facts,
)

# Agent-level facts (e.g., "Last maintenance: 2024-01-15")
# Accessible by all users
```

#### GLOBAL Scope (System-wide)

```python
persistent_facts = PersistentFacts(
    storage=storage,
    scope=MemoryScope.GLOBAL,  # System-wide facts
)

# Global facts (e.g., "System version: 1.0.0")
# Shared across all agents and users
```

---

### 3. Fact Extraction Examples

#### Automatic Extraction (Default)

```python
agent = Agent(
    storage=storage,
    enable_persistent_facts=True,  # Automatic extraction enabled
)

# User shares information
await agent.invoke(
    "My name is John Doe. I live in NYC and love hiking. "
    "I prefer dark mode UI and morning meetings.",
    user_id="[email protected]"
)

# Agent automatically extracts:
# - name: "John Doe"
# - location: "NYC"
# - interests: ["hiking"]
# - preferences: {"ui_theme": "dark", "meeting_time": "morning"}

# Later recall
await agent.invoke(
    "What do you know about me?",
    user_id="[email protected]"
)
# Agent recalls all extracted facts
```

#### Template-Based Extraction

```python
persistent_facts = PersistentFacts(
    storage=storage,
    extraction_template="""
    Extract user information in this format:

    User Profile:
    - Name: {name}
    - Location: {location}
    - Preferences:
      - UI Theme: {ui_theme}
      - Language: {language}
    - Interests: {interests}
    - Goals: {goals}
    """,
)

agent = Agent(
    storage=storage,
    persistent_facts=persistent_facts,
)

# Agent extracts facts matching template structure
```

#### Explicit Fact Management

```python
# Access PersistentFacts directly for explicit control
persistent_facts = agent.persistent_facts

# Add fact explicitly
await persistent_facts.add(
    key="user_preferences",
    value={"theme": "dark", "language": "en"},
    scope=MemoryScope.USER,
    scope_id="[email protected]"
)

# Get fact
prefs = await persistent_facts.get(
    key="user_preferences",
    scope=MemoryScope.USER,
    scope_id="[email protected]"
)

# Update fact
await persistent_facts.update(
    key="user_preferences",
    value={"theme": "light", "language": "en"},  # Updated theme
    scope=MemoryScope.USER,
    scope_id="[email protected]"
)

# Search facts
results = await persistent_facts.search(
    query="preferences",
    scope=MemoryScope.USER,
    scope_id="[email protected]"
)

# Delete fact
await persistent_facts.delete(
    key="user_preferences",
    scope=MemoryScope.USER,
    scope_id="[email protected]"
)
```

---

### 4. Complete Usage Example

```python
import asyncio
from framework.agents import Agent
from framework.memory import PersistentFacts, MemoryScope
from framework.models.openai import OpenAI
from framework.storage.databases.libsql import LibSQLStorage

async def main():
    # Setup
    storage = LibSQLStorage(url="sqlite+aiosqlite:///./demo.db")
    await storage.connect()

    model = OpenAI(model_id="gpt-4o-mini")

    # Initialize agent with persistent facts
    agent = Agent(
        name="PersonalAssistant",
        instructions="You are a helpful personal assistant.",
        model=model,
        storage=storage,
        enable_persistent_facts=True,  # Enable LTM
    )

    user_id = "[email protected]"

    # Conversation 1: User shares information
    response1 = await agent.invoke(
        "Hi! My name is Sarah. I'm a software engineer from San Francisco. "
        "I love hiking and prefer dark mode interfaces.",
        user_id=user_id,
        thread_id="thread_1"
    )
    # Agent automatically extracts:
    # - name: "Sarah"
    # - profession: "software engineer"
    # - location: "San Francisco"
    # - interests: ["hiking"]
    # - preferences: {"ui_theme": "dark"}

    # Conversation 2: Different thread, same user
    response2 = await agent.invoke(
        "What's my name and where am I from?",
        user_id=user_id,
        thread_id="thread_2"  # Different thread
    )
    # Agent recalls: "Your name is Sarah and you're from San Francisco"

    # Conversation 3: Update preferences
    response3 = await agent.invoke(
        "Actually, I prefer light mode now.",
        user_id=user_id,
        thread_id="thread_3"
    )
    # Agent updates: preferences.ui_theme = "light"

    # Explicit fact access
    facts = await agent.persistent_facts.get_all(
        scope=MemoryScope.USER,
        scope_id=user_id
    )
    print(f"Stored facts: {facts}")

    await storage.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 5. API Design

#### PersistentFacts Class

```python
class PersistentFacts:
    """Long-term declarative memory for facts and preferences."""

    def __init__(
        self,
        storage: StorageBackend,
        scope: MemoryScope = MemoryScope.USER,
        auto_extract: bool = True,
        extraction_model: Model | None = None,
        extraction_template: str | None = None,
    ):
        """
        Initialize PersistentFacts.

        Args:
            storage: Storage backend instance
            scope: Default memory scope (USER, SESSION, AGENT, GLOBAL)
            auto_extract: Enable automatic fact extraction from conversations
            extraction_model: Model for extraction (uses agent's model if None)
            extraction_template: Template for structured extraction
        """

    # CRUD Operations
    async def add(
        self,
        key: str,
        value: Any,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Fact:
        """Add a new fact."""

    async def get(
        self,
        key: str,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
    ) -> Fact | None:
        """Retrieve a fact by key."""

    async def update(
        self,
        key: str,
        value: Any,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
    ) -> Fact:
        """Update an existing fact."""

    async def delete(
        self,
        key: str,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
    ) -> bool:
        """Delete a fact."""

    # Search & Retrieval
    async def search(
        self,
        query: str,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
        limit: int = 10,
    ) -> list[Fact]:
        """Search facts by keyword."""

    async def get_all(
        self,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
    ) -> list[Fact]:
        """Get all facts for a scope."""

    # Fact Extraction
    async def extract_from_messages(
        self,
        messages: list[dict[str, Any]],
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
    ) -> list[Fact]:
        """Extract facts from conversation messages."""

    # Intelligent Updates
    async def update_intelligent(
        self,
        facts: list[Fact],
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
    ) -> list[FactUpdate]:
        """
        Intelligently update facts (ADD/UPDATE/DELETE/NOOP).

        Returns list of update operations performed.
        """
```

#### MemoryScope Enum

```python
class MemoryScope(str, Enum):
    """Memory scoping levels."""
    USER = "user"        # User-specific (e.g., preferences)
    SESSION = "session"  # Session-specific (temporary)
    AGENT = "agent"      # Agent-specific (shared across users)
    GLOBAL = "global"    # System-wide (shared by all)
```

#### Fact Model

```python
class Fact(BaseModel):
    """A single persistent fact."""

    id: str
    key: str
    value: Any  # JSON-serializable value
    scope: MemoryScope
    scope_id: str | None  # user_id, session_id, agent_id, etc.
    schema_type: str | None  # Optional schema name for validation
    tags: list[str] = []
    metadata: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    deleted_at: datetime | None = None
```

#### FactUpdate Model

```python
class FactUpdate(BaseModel):
    """Result of intelligent fact update."""

    operation: Literal["ADD", "UPDATE", "DELETE", "NOOP"]
    fact: Fact | None
    reason: str  # Why this operation was chosen
```

---

### 6. Integration with Agent

#### Agent Class Extension

```python
class Agent:
    def __init__(
        self,
        # ... existing params ...
        enable_persistent_facts: bool = False,
        persistent_facts: PersistentFacts | None = None,
    ):
        """
        Initialize Agent.

        Args:
            enable_persistent_facts: Enable persistent facts (auto-initializes)
            persistent_facts: Explicit PersistentFacts instance (overrides enable_persistent_facts)
        """
        # ... existing initialization ...

        # Initialize persistent facts
        if persistent_facts:
            self.persistent_facts = persistent_facts
        elif enable_persistent_facts:
            # Auto-initialize with defaults
            self.persistent_facts = PersistentFacts(
                storage=self.storage,
                scope=MemoryScope.USER,
                auto_extract=True,
            )
        else:
            self.persistent_facts = None

    async def invoke(self, message: str, *, user_id: str | None = None, **kwargs):
        """Invoke agent with persistent facts integration."""
        # ... existing logic ...

        # Extract facts if enabled
        if self.persistent_facts and self.persistent_facts.auto_extract:
            scope_id = user_id or kwargs.get("thread_id")
            facts = await self.persistent_facts.extract_from_messages(
                messages=[{"role": "user", "content": message}],
                scope=MemoryScope.USER,
                scope_id=scope_id,
            )
            # Store extracted facts
            await self.persistent_facts.update_intelligent(facts, scope_id=scope_id)

        # Retrieve relevant facts for context
        if self.persistent_facts and user_id:
            relevant_facts = await self.persistent_facts.get_all(
                scope=MemoryScope.USER,
                scope_id=user_id,
            )
            # Add facts to context
            # ... integrate into messages ...

        # ... rest of invoke logic ...
```

---

### 7. Storage Schema

```sql
CREATE TABLE astra_facts (
    id VARCHAR(64) PRIMARY KEY,
    key VARCHAR(255) NOT NULL,
    value JSON NOT NULL,
    scope VARCHAR(32) NOT NULL,  -- 'user', 'session', 'agent', 'global'
    scope_id VARCHAR(64),        -- user_id, session_id, agent_id, etc.
    schema_type VARCHAR(128),   -- Optional schema name
    tags TEXT[],                -- Array of tags
    metadata JSON,              -- Additional metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,       -- Optional expiration
    deleted_at TIMESTAMP,        -- Soft delete

    -- Indexes
    INDEX idx_facts_key_scope (key, scope, scope_id),
    INDEX idx_facts_scope (scope, scope_id),
    INDEX idx_facts_tags (tags),
    INDEX idx_facts_created (created_at),
    INDEX idx_facts_deleted (deleted_at)
);
```

---

## Conclusion

Astra has **excellent storage infrastructure** but lacks **dedicated LTM features**. To match Agno and Mastra, Astra needs:

1. **Persistent Facts Storage** (Critical)
2. **Memory Scoping** (Critical)
3. **Fact Extraction** (Critical)
4. **Fact Management APIs** (Critical)

The good news: Astra's storage layer is well-designed and can support LTM with minimal changes. The main work is building the **PersistentFacts** abstraction layer on top of existing storage.

**Next Step**: Implement `PersistentFacts` class with core CRUD operations and memory scoping.
