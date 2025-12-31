# Astra Runtime

**Build AI agents in Python with the Astra Embedded Runtime.**

The Astra Runtime provides a comprehensive embedded API for building intelligent agents with tools, RAG, memory, guardrails, and multi-agent teams.

## 🚀 Quick Start

### Installation

```bash
pip install astra-runtime
```

### Basic Agent

```python
import asyncio
from astra import Agent, HuggingFaceLocal

async def main():
    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a helpful assistant"
    )

    response = await agent.invoke("What is Python?")
    print(response)

asyncio.run(main())
```

## ✨ Features

- 🤖 **Agents**: Intelligent agents with tools, memory, and reasoning
- 📚 **RAG**: Retrieval-Augmented Generation with custom pipelines
- 🗄️ **Storage**: LibSQL (SQLite) and MongoDB backends
- 🧠 **Memory**: Conversation history and persistent facts
- 🛡️ **Guardrails**: PII filtering, content moderation, security
- 🔧 **Tools**: Easy function calling and external integrations
- 👥 **Teams**: Multi-agent collaboration and delegation
- ⚙️ **Middlewares**: Request/response processing pipelines

## 📦 What's Included

### 58 Exported Components

- **Core**: `Agent`, `Tool`, `tool`
- **Models**: `Gemini`, `Bedrock`, `HuggingFaceLocal`, `get_model`
- **Storage**: `LibSQLStorage`, `MongoDBStorage`
- **RAG**: Complete pipeline system with stages, embedders, vector DBs
- **Memory**: `AgentMemory`, `MemoryScope`, `PersistentFacts`
- **Middlewares**: `InputMiddleware`, `OutputMiddleware`
- **Guardrails**: 15+ filters and validators
- **Teams**: `Team`, `TeamMember`, delegation tools

## 📚 Examples

We provide **16 comprehensive examples** covering all features:

### Basic (1-8)

- 01: Basic agent usage
- 02: Background job pattern
- 03: Streaming responses
- 04: Agent with tools
- 05: Agent properties
- 06-07: RAG ingestion
- 08: Advanced configuration

### Advanced (9-16)

- 09: Memory & persistent facts
- 10: Guardrails & safety
- 11: Middlewares
- 12: Team delegation
- 13: Advanced RAG
- 14: **Full-featured production agent**
- 15: Model provider comparison
- 16: Storage backends

See [`examples/`](examples/) directory for all examples.

## 🎯 Use Cases

### Chatbots & Assistants

```python
from astra import Agent, LibSQLStorage, HuggingFaceLocal

storage = LibSQLStorage(url="sqlite+aiosqlite:///./chatbot.db")
await storage.connect()

agent = Agent(
    model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
    instructions="You are a friendly customer support assistant",
    storage=storage
)

# Conversations automatically persist
response = await agent.invoke("Hello!", thread_id="user-123")
```

### RAG-Powered Q&A

```python
from astra import Agent, Rag, HuggingFaceEmbedder, LanceDB

embedder = HuggingFaceEmbedder()
vector_db = LanceDB(uri="./knowledge", embedder=embedder)
rag = Rag(context=RagContext(embedder=embedder, vector_db=vector_db))

# Ingest documents
await rag.ingest("Your documentation here...")

# Query with RAG
agent = Agent(model=model, rag_pipeline=rag)
response = await agent.invoke("What does the documentation say about X?")
```

### Safe Enterprise Agents

```python
from astra import Agent, InputPIIFilter, PIIAction

agent = Agent(
    model=model,
    input_guardrails=[
        InputPIIFilter(action=PIIAction.REDACT, types=["email", "phone"])
    ]
)

# PII is automatically redacted before reaching the model
response = await agent.invoke("My email is [email protected]")
```

## 🏗️ Architecture

Astra provides **three entry points** (embedded runtime is available now):

1. ✅ **Embedded Runtime** (`astra.embedded`) - Direct Python API
2. 🔜 **Client SDK** - Connect to Astra Server
3. 🔜 **REST/GraphQL API** - HTTP integration

This package provides the **Embedded Runtime** for direct Python usage.

## 📖 Documentation

- **Getting Started**: See [examples/](examples/)
- **API Reference**: See [src/astra/embedded/README.md](src/astra/embedded/README.md)
- **Publishing Guide**: See [PUBLISHING.md](PUBLISHING.md)

## 🧪 Testing

```bash
# Run import tests
uv run python tests/test_imports.py

# Run examples
uv run python examples/01_basic_agent.py
uv run python examples/14_full_featured_agent.py
```

## 🔧 Development

### Setup

```bash
cd packages/runtime
uv sync
```

### Project Structure

```
packages/runtime/
├── src/astra/          # Source code
│   ├── __init__.py     # Top-level exports
│   └── embedded/       # Embedded runtime
├── examples/           # 16 usage examples
├── tests/              # Test files
└── pyproject.toml      # Package configuration
```

## 📄 License

[Your License Here]

## 🤝 Contributing

Contributions welcome! Please see our contributing guidelines.

## 🔗 Links

- **Homepage**: [https://github.com/yourusername/astra](https://github.com/yourusername/astra)
- **Issues**: [https://github.com/yourusername/astra/issues](https://github.com/yourusername/astra/issues)
- **Documentation**: [https://astra-docs.example.com](https://astra-docs.example.com)

---

**Ready to build AI agents?** Start with our [examples](examples/)!
