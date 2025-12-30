# RAG (Retrieval-Augmented Generation)

RAG enhances LLM responses by retrieving relevant information from a knowledge base at runtime, reducing hallucinations and providing grounded, accurate answers.

## Mental Model

```
┌─────────────────────────────────────────────────────────────────┐
│                            Rag                                  │
│                                                                 │
│  ┌──────────────────────┐     ┌──────────────────────┐         │
│  │   Ingest Pipeline    │     │    Query Pipeline    │         │
│  │                      │     │                      │         │
│  │  Read → Chunk →      │     │  Retrieve → Return   │         │
│  │  Embed → Store       │     │                      │         │
│  └──────────────────────┘     └──────────────────────┘         │
│                    ↑               ↑                            │
│                    └───────┬───────┘                            │
│                            │                                    │
│                    ┌───────────────┐                            │
│                    │  RagContext   │                            │
│                    │  (embedder,   │                            │
│                    │   vector_db,  │                            │
│                    │   config)     │                            │
│                    └───────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principle**: One shared context, two separate pipelines.

---

## High-Level Design (HLD)

```
User → Rag.ingest() → Ingest Pipeline → Vector DB
User → Rag.query()  → Query Pipeline  → Results
```

### Architecture Layers

| Layer              | Components                                                             |
| ------------------ | ---------------------------------------------------------------------- |
| **User API**       | `Rag.ingest()`, `Rag.query()`                                          |
| **Orchestration**  | `Pipeline` (executes stages)                                           |
| **Stages**         | `ReadStage`, `ChunkStage`, `EmbedStage`, `StoreStage`, `RetrieveStage` |
| **Infrastructure** | `VectorDB`, `Embedder`, `Reader`, `Chunker`                            |

---

## Low-Level Design (LLD)

### Core Components

```
rag/
├── context.py       # RagContext, RagConfig, StageState
├── pipeline.py      # Pipeline, Rag
├── stages/          # Stage implementations
├── embedders/       # Embedding providers
├── vectordb/        # Vector database adapters
├── readers/         # Content readers
└── chunking/        # Text chunking strategies
```

### Component Responsibilities

| Component    | Purpose                                                 |
| ------------ | ------------------------------------------------------- |
| `RagContext` | Holds shared dependencies (embedder, vector_db, config) |
| `RagConfig`  | Pipeline configuration (default_top_k, stream)          |
| `StageState` | Mutable data passed between stages                      |
| `Pipeline`   | Executes a sequence of stages                           |
| `Rag`        | User-facing API wrapping ingest/query pipelines         |

---

## Initialization

```python
from framework.rag import (
    Rag, RagContext, Pipeline,
    HuggingFaceEmbedder, LanceDB
)
from framework.rag.stages import (
    ReadStage, ChunkStage, EmbedStage, StoreStage, RetrieveStage
)

# 1. Create shared context
context = RagContext(
    embedder=HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2"),
    vector_db=LanceDB(uri="./my_kb"),
    config={"default_top_k": 5},
)

# 2. Create pipelines
ingest_pipeline = Pipeline(
    name="ingest",
    stages=[ReadStage(), ChunkStage(), EmbedStage(), StoreStage()],
)

query_pipeline = Pipeline(
    name="query",
    stages=[RetrieveStage(top_k=5)],
)

# 3. Create Rag
rag = Rag(
    context=context,
    ingest_pipeline=ingest_pipeline,
    query_pipeline=query_pipeline,
)
```

---

## Ingest Flow

```
rag.ingest(text="...", name="doc1")
         │
         ▼
┌─────────────────┐
│   ReadStage     │  → Converts source to Document objects
└────────┬────────┘
         ▼
┌─────────────────┐
│   ChunkStage    │  → Splits documents into chunks
└────────┬────────┘
         ▼
┌─────────────────┐
│   EmbedStage    │  → Generates embeddings (from RagContext.embedder)
└────────┬────────┘
         ▼
┌─────────────────┐
│   StoreStage    │  → Stores in vector DB (from RagContext.vector_db)
└────────┬────────┘
         ▼
    content_id
```

**Usage:**

```python
# Single document
content_id = await rag.ingest(text="Python is...", name="Python Guide")

# Batch
ids = await rag.ingest_batch([
    {"text": "...", "name": "doc1"},
    {"path": "./file.txt", "name": "doc2"},
])

# Directory
ids = await rag.ingest_directory("./docs", pattern="*.md", recursive=True)
```

---

## Query Flow

```
rag.query("What is Python?", top_k=3)
         │
         ▼
┌─────────────────┐
│  RetrieveStage  │  → Embeds query, searches vector DB
└────────┬────────┘
         ▼
   list[Document]
```

**Usage:**

```python
results = await rag.query("What is Python?", top_k=3)

for doc in results:
    print(doc.content)
    print(doc.metadata)
```

---

## Agent Integration

### Pattern 1: Ingest separately, then pass to agent

```python
from framework.agents import Agent
from framework.models import Gemini

# Create and ingest BEFORE passing to agent
rag = Rag(...)
await rag.ingest(text="Python is...", name="Python Guide")

# Pass to agent (agent only queries)
agent = Agent(
    name="Assistant",
    model=Gemini("gemini-2.0-flash-exp"),
    instructions="Use retrieve_evidence to answer questions.",
    rag_pipeline=rag,
)

response = await agent.invoke("What is Python?")
```

### Pattern 2: Ingest via agent (recommended for APIs/production)

```python
# Create agent with rag_pipeline
agent = Agent(
    name="Assistant",
    model=Gemini("gemini-2.0-flash-exp"),
    rag_pipeline=rag,
)

# Ingest via agent (convenience methods)
await agent.ingest(text="Python is...", name="Python Guide")

# Batch ingest (ideal for API file uploads)
await agent.ingest_batch([
    {"text": "...", "name": "doc1"},
    {"path": "./uploaded_file.pdf", "name": "User Upload"},
])

# Directory ingest
await agent.ingest_directory("./docs", pattern="*.md", recursive=True)

response = await agent.invoke("What is Python?")
```

**Use this pattern when:**

- Building APIs where users upload files dynamically
- Agent is a singleton that lives across requests
- You want a single object for all RAG operations

Both patterns work. Choose based on your preference.

---

## Stage Reference

| Stage           | Type      | Purpose                                 |
| --------------- | --------- | --------------------------------------- |
| `ReadStage`     | Ingestion | Reads content from files, URLs, or text |
| `ChunkStage`    | Ingestion | Splits documents into chunks            |
| `EmbedStage`    | Both      | Generates embeddings                    |
| `StoreStage`    | Ingestion | Stores chunks in vector DB              |
| `RetrieveStage` | Query     | Retrieves relevant documents            |

---

## Configuration

```python
# RagContext config (dict)
config={
    "default_top_k": 5,   # Default number of results
}

ChunkStage(
    strategy="recursive",
    chunk_size=512,
    chunk_overlap=50,
)

RetrieveStage(
    top_k=10,
    search_type="vector",  # "vector" or "hybrid"
)
```
