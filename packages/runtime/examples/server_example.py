"""
Astra Server Example.

Demonstrates how to create an HTTP server from Astra agents.

Run with:
    uvicorn examples.server_example:app --reload

Then visit:
    - http://localhost:8000/docs - OpenAPI documentation
    - http://localhost:8000/health - Health check
    - http://localhost:8000/v1/meta - Server metadata
    - http://localhost:8000/v1/agents - List agents
"""

from astra import Agent, HuggingFaceLocal
from astra.server import create_app


# Define an agent
assistant = Agent(
    name="assistant",
    model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
    instructions="You are a helpful AI assistant. Answer questions clearly and concisely.",
)

# Create FastAPI app from agents
app = create_app(
    agents={"assistant": assistant},
    name="Astra Demo Server",
    version="1.0.0",
    cors_origins=["*"],  # Allow all origins for demo
    docs_enabled=True,
)

# The app is now ready to serve:
# POST /v1/agents/assistant/generate - Generate response
# POST /v1/agents/assistant/stream - Stream response (SSE)
# GET /v1/agents - List all agents
# GET /v1/agents/assistant - Get agent details
# GET /v1/meta - Server metadata
# GET /health - Health check

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
