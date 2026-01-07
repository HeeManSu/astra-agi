# Astra Framework

🧠 **Core framework for building AI agents, teams, and RAG pipelines.**

This is the foundational layer of Astra - providing all the building blocks for intelligent AI applications.

## Installation

```bash
pip install astra-framework
```

### Optional Dependencies

```bash
# With MongoDB support
pip install astra-framework[mongodb]

# With AWS Bedrock support
pip install astra-framework[aws]

# Everything
pip install astra-framework[all]
```

## Features

| Component         | Description                                            |
| ----------------- | ------------------------------------------------------ |
| 🤖 **Agents**     | Intelligent agents with tools, memory, and context     |
| 📚 **RAG**        | Retrieval-Augmented Generation pipelines               |
| 🗄️ **Storage**    | LibSQL, MongoDB backends                               |
| 🛡️ **Guardrails** | PII filtering, content moderation, injection detection |
| 🔧 **Tools**      | Function calling with `@tool` decorator                |
| 👥 **Teams**      | Multi-agent collaboration and delegation               |
| 💾 **Memory**     | Short-term and long-term agent memory                  |
| 🔌 **Middleware** | Input/output processing pipelines                      |

## Model Support

- Google Gemini
- OpenAI GPT
- AWS Bedrock (Claude, etc.)
- HuggingFace Local Models

## Quick Example

```python
from framework.agents import Agent, tool
from framework.models import Gemini

@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Sunny in {city}"

agent = Agent(
    model=Gemini("gemini-2.0-flash"),
    instructions="You are a helpful assistant",
    tools=[get_weather]
)

response = await agent.invoke("What's the weather in Tokyo?")
```

## Documentation

See [examples](https://github.com/HeeManSu/astra-agi/tree/main/packages/framework/examples) for comprehensive examples.

## Related Packages

- **astra-runtime**: High-level runtime with embedded mode and FastAPI server
- **astra-observability**: Tracing, metrics, and logging

## License

MIT License
