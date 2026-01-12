# Memory System in Astra Framework

## Table of Contents

1. [What is Memory in GenAI?](#what-is-memory-in-genai)
2. [Memory Management](#memory-management)
3. [Types of Memory](#types-of-memory)
4. [How Astra Does It](#how-astra-does-it)
5. [Comparison with Mastra](#comparison-with-mastra)
6. [Mental Model](#mental-model)
7. [High Level Design (HLD)](#high-level-design-hld)
8. [Full Flow](#full-flow)
9. [Low Level Design (LLD)](#low-level-design-lld)
10. [Initialization](#initialization)
11. [Future Scope](#future-scope)

---

## What is Memory in GenAI?

Memory in GenAI systems enables AI agents to:

- **Remember** previous conversations and interactions
- **Maintain context** across multiple turns
- **Learn** user preferences and facts over time
- **Provide continuity** in multi-turn conversations
- **Store declarative knowledge** (facts, preferences, user data)

Unlike traditional stateless APIs, AI agents with memory can build relationships and maintain state, making interactions more natural and personalized.

---

## Memory Management

Memory Management is the orchestration layer that:

- **Loads** conversation history from storage
- **Filters** messages based on configuration (system messages, tool calls)
- **Trims** context to fit within token limits
- **Summarizes** old messages when context exceeds limits
- **Caches** summaries to avoid redundant LLM calls
- **Manages** both short-term (conversation) and long-term (facts) memory

---

## Types of Memory

Astra Framework implements a **dual-memory architecture** inspired by cognitive science:

### 1. Short-Term Memory (STM) - `AgentMemory` + `MemoryManager`

**Purpose**: Maintains recent conversation context

**Characteristics**:

- Ephemeral (per conversation thread)
- Token-aware windowing
- Automatic summarization on overflow
- Configurable message filtering

**Use Cases**:

- Recent conversation history
- Current session context
- Immediate turn-by-turn continuity

### 2. Long-Term Memory (LTM) - `PersistentFacts`

**Purpose**: Stores declarative facts and preferences

**Characteristics**:

- Persistent across sessions
- Scoped (USER/SESSION/AGENT/GLOBAL)
- CRUD operations
- Optional LLM-based fact extraction

**Use Cases**:

- User preferences (theme, language)
- Personal information (name, location)
- Agent-specific facts (maintenance logs)
- Global system facts (version, config)

---

## How Astra Does It

Astra implements a **dual-memory architecture** with the following design principles:

### Core Design Principles:

1. **Dual Memory Architecture**: STM (conversation) + LTM (facts) separation
2. **Token-Aware Management**: Primary token limits with message count fallback
3. **Automatic Summarization**: Overflow handling with LLM summarization
4. **Storage Abstraction**: Database-agnostic storage backend (LibSQL, MongoDB)
5. **Memory Scoping**: Four-level scoping for isolation (USER/SESSION/AGENT/GLOBAL)
6. **Lazy Initialization**: Resources initialized only when needed
7. **Performance Optimization**: Token counter caching, batched writes, summary caching

### Key Features:

- **Integrated Storage**: Uses existing `StorageBackend` - no separate memory storage needed
- **Flexible Fact Extraction**: Optional auto-extraction with customizable LLM templates
- **Configurable Windowing**: Token-based (primary) or message-count (fallback) limiting
- **Smart Filtering**: Configurable system message and tool call filtering
- **Summary Caching**: Avoids redundant LLM calls for identical conversations
- **Queue-Based Writes**: Batched message persistence for performance

---

## Comparison with Mastra

Astra follows similar design patterns to Mastra but with some differences:

### Similarities ✅

1. **Dual Memory Architecture**: Both use STM (conversation) + LTM (facts/preferences)
2. **Token-Aware Management**: Both prioritize token limits with message count fallback
3. **Automatic Summarization**: Both handle overflow with LLM summarization
4. **Storage Abstraction**: Both support multiple storage backends
5. **Memory Scoping**: Both provide scoping for memory isolation
6. **Lazy Initialization**: Both defer expensive operations until needed

### What Mastra Provides That Astra Doesn't (Yet) ❌

#### 1. **Semantic Recall**

**Mastra**: Vector similarity search to retrieve relevant past messages from old conversations

- Uses embeddings to find semantically similar messages
- Prepends relevant historical context to current conversation
- Enables agents to recall information from conversations weeks/months ago

**Astra**: Currently only loads recent conversation history (STM)

- No vector search over past conversations
- No semantic retrieval of old messages

**Impact**: Mastra can provide better long-term context by finding relevant past conversations, while Astra is limited to recent history.

#### 2. **Memory Processors**

**Mastra**: Pluggable memory processors that transform/filter messages

- `MessageHistory` processor: Retrieves and persists messages
- `SemanticRecall` processor: Performs vector similarity searches
- `WorkingMemory` processor: Manages working memory state
- Custom processors can be added

**Astra**: Built-in memory management without processor abstraction

- Memory logic is embedded in `MemoryManager`
- Less flexible for custom memory transformations

**Impact**: Mastra's processor pattern allows more customization and composability.

#### 3. **Working Memory Concept**

**Mastra**: Structured "Working Memory" for user-specific persistent details

- Explicit concept separate from conversation history
- Thread-scoped vs Resource-scoped distinction
- Designed specifically for user preferences, names, goals

**Astra**: Uses `PersistentFacts` which is more generic

- Facts can store anything, not specifically structured for "working memory"
- Less semantic distinction between different types of persistent data

**Impact**: Mastra's Working Memory provides clearer semantics for user-specific data.

#### 4. **Resource-Scoped Memory**

**Mastra**: Resource-scoped memory persists across ALL threads for the same user

- User-level memory that spans multiple conversation threads
- Enables consistent experience across different conversations

**Astra**: USER scope exists but may not be explicitly "resource-scoped"

- USER scope facts are scoped to user_id but threading may differ
- Less explicit about cross-thread persistence

**Impact**: Mastra's resource-scoping provides clearer semantics for user-wide memory.

#### 5. **Additional Storage Options**

**Mastra**: Supports PostgreSQL and Upstash in addition to LibSQL and MongoDB

**Astra**: Currently supports LibSQL and MongoDB

**Impact**: Mastra offers more deployment flexibility.

### What Astra Provides That Mastra Doesn't ✅

#### 1. **Four-Level Scoping**

**Astra**: USER/SESSION/AGENT/GLOBAL scoping

- More granular control over memory isolation
- AGENT scope for agent-specific facts shared across users
- GLOBAL scope for system-wide facts

**Mastra**: Primarily Thread-scoped and Resource-scoped

#### 2. **Integrated Storage**

**Astra**: Uses existing `StorageBackend` - no separate memory storage layer

- Simpler architecture
- Reuses storage infrastructure

**Mastra**: May have separate memory storage abstraction

#### 3. **Summary Caching**

**Astra**: Caches summaries by thread_id to avoid redundant LLM calls

- Performance optimization for repeated queries

**Mastra**: May regenerate summaries each time

### Future Enhancements for Astra

Based on Mastra's features, potential additions:

1. **Semantic Recall**

   ```python
   # Future: Vector-based semantic recall
   semantic_memory = SemanticMemory(
       vector_db=vector_db,
       embedder=embedder,
   )
   relevant_messages = await semantic_memory.recall(
       query="user preferences",
       thread_id=thread_id,
       limit=5
   )
   ```

2. **Memory Processors**

   ```python
   # Future: Pluggable processors
   memory_processors = [
       MessageHistoryProcessor(),
       SemanticRecallProcessor(vector_db=vector_db),
       WorkingMemoryProcessor(),
   ]
   agent = Agent(..., memory_processors=memory_processors)
   ```

3. **Working Memory Abstraction**

   ```python
   # Future: Explicit Working Memory
   working_memory = WorkingMemory(
       storage=storage,
       scope=MemoryScope.RESOURCE,  # Across all threads
   )
   ```

4. **Additional Storage Backends**
   - PostgreSQL support
   - Upstash support
   - Redis support for caching

---

## Mental Model

Think of memory as a **two-tier system**:

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐      ┌──────────────────┐      │
│  │  Short-Term      │      │  Long-Term        │      │
│  │  Memory (STM)    │      │  Memory (LTM)     │      │
│  │                  │      │                  │      │
│  │  • Recent        │      │  • User Facts     │      │
│  │    conversation  │      │  • Preferences    │      │
│  │  • Context       │      │  • Declarative    │      │
│  │    window        │      │    knowledge      │      │
│  │  • Token-aware   │      │  • Scoped         │      │
│  │    trimming      │      │    (USER/AGENT/   │      │
│  │  • Summarization │      │     GLOBAL)       │      │
│  └──────────────────┘      └──────────────────┘      │
│         │                          │                   │
│         └──────────┬────────────────┘                  │
│                    │                                    │
│         ┌──────────▼──────────┐                        │
│         │   AgentStorage      │                        │
│         │   (Storage Layer)   │                        │
│         └─────────────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

**STM** = Working memory (what the agent is thinking about right now)
**LTM** = Permanent knowledge (what the agent knows about users/domain)

---

## High Level Design (HLD)

### Component Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Agent Layer                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Agent                                                │   │
│  │  • memory: AgentMemory                                │   │
│  │  • memory_manager: MemoryManager                     │   │
│  │  • persistent_facts: PersistentFacts                │   │
│  │  • storage: AgentStorage                             │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                  Memory Management Layer                     │
│  ┌──────────────────┐         ┌──────────────────┐       │
│  │ MemoryManager     │         │ PersistentFacts   │       │
│  │                   │         │                   │       │
│  │ • get_context()  │         │ • add()           │       │
│  │ • Token limiting  │         │ • get()           │       │
│  │ • Summarization  │         │ • update()        │       │
│  │ • Message filter │         │ • delete()        │       │
│  │ • Window mgmt     │         │ • extract_from_   │       │
│  │                   │         │   messages()      │       │
│  └──────────────────┘         └──────────────────┘       │
│         │                              │                   │
│         │                              │                   │
│  ┌──────▼──────┐              ┌───────▼────────┐         │
│  │TokenCounter │              │   FactStore     │         │
│  │             │              │                 │         │
│  │ • count()   │              │ • CRUD ops      │         │
│  │ • cache     │              │ • Search        │         │
│  └─────────────┘              └─────────────────┘         │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                      Storage Layer                            │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ AgentStorage     │         │ StorageBackend   │         │
│  │                  │         │                  │         │
│  │ • add_message()  │         │ • LibSQLStorage  │         │
│  │ • get_history()  │         │ • MongoDBStorage │         │
│  │ • ThreadStore    │         │                  │         │
│  │ • MessageStore   │         │                  │         │
│  └──────────────────┘         └──────────────────┘         │
└──────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. `AgentMemory` (Configuration)

- **Purpose**: Configuration model for STM behavior
- **Key Settings**:
  - `token_limit`: Primary token-based windowing
  - `window_size`: Fallback message count limit
  - `summarize_overflow`: Enable/disable summarization
  - `include_system_messages`: Filter system messages
  - `include_tool_calls`: Filter tool call messages

#### 2. `MemoryManager` (STM Orchestrator)

- **Purpose**: Manages conversation context loading and trimming
- **Responsibilities**:
  - Load messages from storage
  - Apply token-aware or message-count limiting
  - Generate summaries for overflow messages
  - Filter messages based on configuration
  - Cache summaries for performance

#### 3. `PersistentFacts` (LTM Manager)

- **Purpose**: Manages long-term declarative memory
- **Responsibilities**:
  - CRUD operations for facts
  - Memory scoping (USER/SESSION/AGENT/GLOBAL)
  - LLM-based fact extraction from conversations
  - Fact search and retrieval

#### 4. `TokenCounter` (Utility)

- **Purpose**: Accurate token counting with caching
- **Features**:
  - Uses tiktoken for accurate counting
  - Includes message/conversation overhead
  - Caching for performance
  - Fallback to character estimation

#### 5. `AgentStorage` (Storage Facade)

- **Purpose**: High-level interface for conversation storage
- **Responsibilities**:
  - Thread management
  - Message persistence
  - History retrieval
  - Batched writes via queue

---

## Full Flow

### Agent Invocation with Memory

```
┌─────────────────────────────────────────────────────────────┐
│  1. User sends message: "What is my name?"                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Agent.invoke() called                                   │
│     • Validates input                                       │
│     • Prepares execution context                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Load Conversation Context (STM)                        │
│     MemoryManager.get_context()                             │
│     ├─> AgentStorage.get_history(thread_id)                │
│     ├─> Filter messages (tool calls, system)              │
│     ├─> Apply token-aware limiting                         │
│     │   ├─> Count tokens for each message                  │
│     │   ├─> Trim oldest messages if exceed limit          │
│     │   └─> Summarize overflow if enabled                 │
│     └─> Return context messages                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Load Persistent Facts (LTM)                             │
│     PersistentFacts.get_all(scope_id=user_id)             │
│     ├─> Query FactStore                                    │
│     ├─> Filter by scope                                    │
│     └─> Return relevant facts                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Build Model Messages                                    │
│     [system] + [facts] + [context] + [user_message]        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Invoke LLM                                             │
│     model.invoke(messages)                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  7. Save Response                                           │
│     AgentStorage.add_message()                             │
│     ├─> Queue message for batch write                      │
│     └─> Persist to storage                                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  8. Extract Facts (Optional)                               │
│     PersistentFacts.extract_from_messages()               │
│     ├─> Format conversation for extraction                │
│     ├─> Invoke LLM with extraction template               │
│     ├─> Parse JSON response                                │
│     └─> Save extracted facts                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  9. Return Response to User                                 │
└─────────────────────────────────────────────────────────────┘
```

### Token-Aware Windowing Flow

```
Messages: [M1, M2, M3, ..., M20]  (20 messages)
Token Limit: 1000 tokens

┌─────────────────────────────────────────────────────────────┐
│ Step 1: Load Messages                                      │
│   Load 2x window_size (40 messages) for buffer             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Filter Messages                                    │
│   • Exclude tool calls (if configured)                     │
│   • Separate system vs non-system                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Count Tokens                                       │
│   • System messages: 150 tokens                            │
│   • Non-system messages: 1200 tokens                       │
│   • Total: 1350 tokens (exceeds limit!)                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Trim Messages                                      │
│   • Reserve 200 tokens for summary                          │
│   • Available: 1000 - 200 = 800 tokens                     │
│   • System: 150 tokens                                      │
│   • Non-system budget: 800 - 150 = 650 tokens             │
│   • Keep newest messages that fit                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Summarize Overflow                                  │
│   • Old messages: M1-M10 (500 tokens)                      │
│   • Generate summary: "User discussed Python, AI..."         │
│   • Summary: 50 tokens                                       │
│   • Final: [system_msgs] + [summary] + [recent_msgs]      │
└─────────────────────────────────────────────────────────────┘
```

---

## Low Level Design (LLD)

### MemoryManager Logic

#### `get_context()` Method Flow

```python
async def get_context(thread_id, storage, max_tokens):
    # 1. Check if history is enabled
    if not self.memory.add_history_to_messages:
        return []

    # 2. Calculate window size
    message_limit = self.memory.window_size
    if window_size == default and num_history_responses != default:
        message_limit = num_history_responses * 2

    # 3. Load messages (2x limit for buffer)
    recent_messages = await storage.get_history(thread_id, limit=message_limit * 2)

    # 4. Convert to dict format
    context = [storage._message_to_dict(msg) for msg in recent_messages]

    # 5. Filter tool calls if disabled
    if not self.memory.include_tool_calls:
        context = [msg for msg in context if msg.get("role") != "tool"]

    # 6. Apply limiting strategy
    if self.memory.token_limit and max_tokens:
        context = await self._apply_token_limiting(context, max_tokens)
    else:
        context = self._apply_message_limiting(context, message_limit)

    return context
```

#### Token Limiting Algorithm

```python
async def _apply_token_limiting(messages, max_tokens):
    # 1. Reserve tokens for summary
    summary_reserve = 200 if self.memory.summarize_overflow else 0
    available_tokens = max_tokens - summary_reserve

    # 2. Separate system and non-system messages
    system_messages = [msg for msg in messages if msg.get("role") == "system"]
    non_system_messages = [msg for msg in messages if msg.get("role") != "system"]

    # 3. Count system message tokens
    system_tokens = sum(self._token_counter.count_message(msg) for msg in system_messages)

    # 4. Calculate budget for non-system messages
    non_system_budget = available_tokens - system_tokens

    # 5. Trim non-system messages (keep newest)
    trimmed = []
    current_tokens = 0
    for msg in reversed(non_system_messages):
        msg_tokens = self._token_counter.count_message(msg)
        if current_tokens + msg_tokens <= non_system_budget:
            trimmed.insert(0, msg)
            current_tokens += msg_tokens
        else:
            break

    # 6. Check if summarization needed
    total_tokens = self._token_counter.count_input_messages(all_messages)
    if total_tokens > max_tokens and self.memory.summarize_overflow:
        summary = await self._get_summary_for_overflow(all_messages, trimmed, max_tokens)
        if summary:
            summary_msg = {"role": "system", "content": f"Previous conversation summary: {summary}"}
            return [*system_messages, summary_msg, *trimmed]

    return system_messages + trimmed
```

### PersistentFacts Logic

#### Fact Extraction Flow

```python
async def extract_from_messages(messages, scope_id):
    # 1. Check if extraction enabled
    if not self.auto_extract:
        return []

    # 2. Get extraction model
    extraction_model = self.extraction_model or agent_model
    if not extraction_model:
        return []

    # 3. Format conversation
    conversation_text = "\n".join([
        f"{msg.get('role')}: {msg.get('content')}"
        for msg in messages
    ])

    # 4. Build extraction prompt
    prompt = f"{self.extraction_template}\n\nConversation:\n{conversation_text}\n\nExtract facts as JSON:"

    # 5. Invoke LLM
    response = await extraction_model.invoke([{"role": "user", "content": prompt}])

    # 6. Parse and create facts
    extracted_data = json.loads(response.content)
    facts = []
    for key, value in extracted_data.items():
        fact = Fact(
            id=f"fact-{uuid4().hex[:12]}",
            key=key,
            value=value,
            scope=self.scope,
            scope_id=scope_id,
            tags=["extracted"],
        )
        facts.append(fact)

    return facts
```

#### Memory Scoping Logic

```python
# USER Scope (most common)
fact = await persistent_facts.add(
    key="user_name",
    value="Alice",
    scope_id="user_123"  # Required for USER scope
)
# Only accessible when scope_id="user_123"

# SESSION Scope (temporary)
fact = await persistent_facts.add(
    key="current_task",
    value="writing report",
    scope=MemoryScope.SESSION,
    scope_id="thread_456"
)
# Only accessible for thread_456

# AGENT Scope (shared across users)
fact = await persistent_facts.add(
    key="last_maintenance",
    value="2024-01-15",
    scope=MemoryScope.AGENT,
    scope_id="agent_789"
)
# All users of agent_789 can access

# GLOBAL Scope (system-wide)
fact = await persistent_facts.add(
    key="system_version",
    value="1.0.0",
    scope=MemoryScope.GLOBAL
)
# Everyone can access, scope_id ignored
```

---

## Initialization

### Basic Agent with Memory

```python
from framework.agents import Agent
from framework.memory.memory import AgentMemory
from framework.storage.databases.libsql import LibSQLStorage

# Initialize storage
storage = LibSQLStorage(url="sqlite+aiosqlite:///./agent.db")
await storage.connect()

# Configure memory
memory_config = AgentMemory(
    token_limit=2000,           # Primary: token-based windowing
    window_size=20,             # Fallback: message count
    summarize_overflow=True,     # Summarize old messages
    include_system_messages=True,
    include_tool_calls=False,
)

# Create agent with memory
agent = Agent(
    name="MemoryAgent",
    instructions="You are a helpful assistant.",
    model=model,
    storage=storage,
    memory=memory_config,
)
```

### Agent with Persistent Facts

```python
from framework.memory.persistent_facts import PersistentFacts, MemoryScope

# Option 1: Auto-initialize
agent = Agent(
    name="FactsAgent",
    instructions="Remember user preferences.",
    model=model,
    storage=storage,
    enable_persistent_facts=True,  # Auto-creates PersistentFacts
)

# Option 2: Custom PersistentFacts
persistent_facts = PersistentFacts(
    storage=storage,
    scope=MemoryScope.USER,
    auto_extract=True,
    extraction_model=model,
)

agent = Agent(
    name="CustomFactsAgent",
    instructions="Remember user preferences.",
    model=model,
    storage=storage,
    persistent_facts=persistent_facts,
)
```

### Using Memory in Agent Invocation

```python
# Agent automatically loads context and facts
response = await agent.invoke(
    "What did we discuss earlier?",
    thread_id="thread_123"
)

# Access persistent facts manually
if agent.persistent_facts:
    fact = await agent.persistent_facts.get(
        key="user_name",
        scope_id="user_456"
    )

    # Add facts manually
    await agent.persistent_facts.add(
        key="preference",
        value="dark_mode",
        scope_id="user_456"
    )
```

---

## Future Scope

### Planned Enhancements

1. **Episodic Memory**

   - Store conversation episodes as retrievable units
   - Semantic search over past conversations
   - Context-aware episode retrieval

2. **Memory Compression**

   - Advanced summarization techniques
   - Hierarchical memory compression
   - Selective memory retention

3. **Memory Analytics**

   - Memory usage metrics
   - Token consumption tracking
   - Memory efficiency optimization

4. **Multi-Modal Memory**

   - Store images, documents in memory
   - Cross-modal memory retrieval
   - Rich context embedding

5. **Memory Sharing**

   - Cross-agent memory sharing
   - Team memory pools
   - Memory inheritance

6. **Advanced Fact Extraction**

   - Structured fact schemas
   - Fact validation and verification
   - Temporal fact tracking

7. **Memory Backends**

   - Vector database integration
   - Distributed memory storage
   - Memory replication

8. **Memory Policies**
   - Configurable retention policies
   - Automatic fact expiration
   - Memory cleanup strategies

---

## Summary

Astra's memory system provides a **dual-memory architecture** that combines:

- **Short-Term Memory**: Token-aware conversation context with automatic summarization
- **Long-Term Memory**: Scoped persistent facts with optional LLM extraction

The system is designed to be:

- **Fast**: Caching, batched writes, efficient token counting
- **Flexible**: Configurable windowing, filtering, scoping
- **Scalable**: Database-agnostic storage, lazy initialization
- **Observable**: Built-in tracing and metrics support

This architecture enables AI agents to maintain context, learn preferences, and provide personalized experiences across multiple interactions.
