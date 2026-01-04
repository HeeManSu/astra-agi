"""
Simple Astra Server for Playground Testing.

Run with:
    uvicorn examples.simple_server:app --reload --port 8000
"""

from astra import Agent, HuggingFaceLocal
from astra.server import create_app


# Simple agents without storage for quick testing
assistant = Agent(
    name="assistant",
    model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
    instructions="You are a helpful AI assistant. Be concise and friendly.",
)

code_expert = Agent(
    name="code-expert",
    model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
    instructions="You are an expert programmer. Help with code questions.",
)

# Create the app
app = create_app(
    agents={
        "assistant": assistant,
        "code-expert": code_expert,
    },
    name="Astra Playground Demo",
    version="1.0.0",
    cors_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
