# Astra Runtime

🚀 **Build AI agents, teams, and RAG pipelines in pure Python.**

Astra Runtime provides everything you need to build intelligent AI applications:

- **Embedded Mode**: Use agents directly in your Python code
- **Server Mode**: Deploy as REST APIs with FastAPI

[![PyPI version](https://badge.fury.io/py/astra-runtime.svg)](https://badge.fury.io/py/astra-runtime)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install astra-runtime
```

### Optional Dependencies

```bash
# With MongoDB support
pip install astra-runtime[mongodb]

# With AWS Bedrock support
pip install astra-runtime[aws]

# Everything
pip install astra-runtime[all]
```

## Quick Start

### Embedded Mode

```python
import asyncio
from astra import Agent, Gemini

agent = Agent(
    model=Gemini(model="gemini-2.0-flash"),
    instructions="You are a helpful assistant"
)

async def main():
    response = await agent.invoke("Hello!")
    print(response.content)

asyncio.run(main())
```

### Server Mode

```python
from astra import Agent, Gemini
from astra.server import create_app

agent = Agent(
    name="assistant",
    model=Gemini(model="gemini-2.0-flash"),
    instructions="You are a helpful assistant"
)

app = create_app(agents={"assistant": agent})

# Run with: uvicorn main:app --reload
```

### With Tools

```python
from astra import Agent, Tool, tool, Gemini

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"The weather in {city} is sunny, 72°F"

agent = Agent(
    model=Gemini(model="gemini-2.0-flash"),
    instructions="You are a weather assistant",
    tools=[get_weather]
)
```

### RAG (Retrieval-Augmented Generation)

```python
from astra import Agent, Rag, LanceDB, HuggingFaceEmbedder, Gemini

# Create RAG pipeline
rag = Rag(
    vector_db=LanceDB(path="./my_db"),
    embedder=HuggingFaceEmbedder()
)

# Ingest documents
await rag.ingest("path/to/documents/")

# Create agent with RAG
agent = Agent(
    model=Gemini(model="gemini-2.0-flash"),
    instructions="Answer questions using the provided context",
    rag=rag
)
```

## Features

| Feature           | Description                                                   |
| ----------------- | ------------------------------------------------------------- |
| 🤖 **Agents**     | Build intelligent agents with tools, memory, and context      |
| 📚 **RAG**        | Retrieval-Augmented Generation with custom pipelines          |
| 🗄️ **Storage**    | LibSQL, MongoDB, and LanceDB backends                         |
| 🛡️ **Guardrails** | PII filtering, content moderation, prompt injection detection |
| 🔧 **Tools**      | Easy function calling with `@tool` decorator                  |
| 👥 **Teams**      | Multi-agent collaboration and delegation                      |
| 🌐 **Server**     | FastAPI-based REST API with streaming support                 |
| 💾 **Memory**     | Short-term and long-term agent memory                         |
| 🔌 **Middleware** | Input/output processing pipelines                             |

## Model Support

- **Google Gemini**: `Gemini(model="gemini-2.0-flash")`
- **OpenAI**: `OpenAI(model="gpt-4")`
- **AWS Bedrock**: `Bedrock(model="anthropic.claude-3")`
- **HuggingFace Local**: `HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct")`

## Documentation

- 📖 [Examples](https://github.com/HeeManSu/astra-agi/tree/main/packages/runtime/examples)
- 🐛 [Issues](https://github.com/HeeManSu/astra-agi/issues)
- 💬 [Discussions](https://github.com/HeeManSu/astra-agi/discussions)

## License

MIT License - see [LICENSE](LICENSE) for details.
