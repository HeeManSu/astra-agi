"""
Test Server for Playground API Testing

This server creates multiple test agents for testing and debugging
the Astra Playground API endpoints, especially `/api/v1/agents`.

Uses local Hugging Face models (Qwen2.5-1.5B-Instruct) for cost-free testing.
Models will be downloaded on first run (~1.5GB each).

Run with:
    cd packages/runtime
    uv run --package astra-runtime python examples/test_server/main.py

Or use VS Code debugger with "Python: Test Server - Playground API" configuration.

Requirements:
    - transformers
    - torch
    - accelerate (optional, for better GPU support)

Access:
    - API Docs: http://127.0.0.1:8000/docs
    - Playground Agents: http://127.0.0.1:8000/api/v1/agents
    - Playground UI: http://127.0.0.1:8000/
"""

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

# PYTHONPATH Setup for Uvicorn Reload
#
# WHY THIS IS NEEDED:
# When using `uv run --package astra-runtime`, uv automatically resolves
# workspace dependencies for the main process. However, uvicorn's reload feature
# spawns a subprocess that needs to import "examples.test_server.main:app" as a module.
# The subprocess needs runtime_dir in PYTHONPATH to find the "examples" package.
#
# This is REQUIRED for uvicorn reload to work correctly, regardless of how
# we run the script (uv run or python directly).

current_dir = Path(__file__).parent
runtime_dir = current_dir.parent.parent

# Set PYTHONPATH environment variable for uvicorn reload subprocess
runtime_path = str(runtime_dir)
pythonpath = os.environ.get("PYTHONPATH", "")
if runtime_path not in pythonpath:
    os.environ["PYTHONPATH"] = f"{runtime_path}:{pythonpath}" if pythonpath else runtime_path

# Imports - uv run automatically resolves workspace dependencies
# These must come after PYTHONPATH setup for uvicorn reload to work
from astra.server import AstraServer  # noqa: E402
from framework.agents.agent import Agent  # noqa: E402
from framework.agents.tool import tool  # noqa: E402
from framework.models.huggingface.local import HuggingFaceLocal  # noqa: E402
from framework.storage.databases.mongodb import MongoDBStorage  # noqa: E402
import uvicorn  # noqa: E402


@tool
def calculator(operation: str, a: float, b: float) -> float:
    """Perform basic math operations."""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        return a / b if b != 0 else 0.0
    return 0.0


@tool
def get_weather(city: str) -> str:
    """Get weather information for a city."""
    return f"The weather in {city} is sunny, 72°F"


# Create app at module level for uvicorn reload support
# Note: Storage objects are created synchronously here, but async connection
# happens automatically via FastAPI's lifespan handler when server starts
print("Creating test server...")

print("Creating agent 1...")
agent1 = Agent(
    name="Agent 1",
    id="agent-1",
    model=HuggingFaceLocal("Qwen/Qwen2.5-1.5B-Instruct"),
    instructions="You are a helpful assistant that provides clear and concise answers.",
    description="A simple assistant agent with no tools or storage",
)

agent2 = Agent(
    name="Agent 2",
    id="agent-2",
    model=HuggingFaceLocal("Qwen/Qwen2.5-1.5B-Instruct"),
    instructions="You are a helpful assistant that can perform calculations and get weather information.",
    description="An agent with multiple tools for testing",
    tools=[calculator, get_weather],
)

mongo_storage = MongoDBStorage(
    url=os.getenv("MONGODB_URL", "mongodb://localhost:27017"),
    db_name="astra_test_server",
)

print("Creating agent 3...")
agent3 = Agent(
    name="Agent 3",
    id="agent-3",
    model=HuggingFaceLocal("Qwen/Qwen2.5-1.5B-Instruct"),
    instructions="You are a helpful assistant that can perform calculations and get weather information.",
    description="An agent with multiple tools for testing",
    tools=[calculator, get_weather],
    storage=mongo_storage,
)

print("Creating agent 4...")
agent4 = Agent(
    name="Agent 4",
    id="agent-4",
    model=HuggingFaceLocal("Qwen/Qwen2.5-1.5B-Instruct"),
    instructions="You are a financial advisor that can provide financial advice and investment recommendations.",
    description="An agent that can provide financial advice and investment recommendations.",
)

agents = [agent1, agent2, agent3, agent4]
print("Creating server...")
server = AstraServer(
    agents=agents,
    name="Astra Test Server",
    version="1.0.0",
    description="Test server for Playground API endpoints",
    docs_enabled=True,
    storage=mongo_storage,
    playground_enabled=True,
    cors={
        "origins": ["http://127.0.0.1:8000", "http://localhost:8000", "*"],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    },
    secret=os.getenv("ASTRA_JWT_SECRET", "dev-secret-for-testing"),
    debug_mode=True,
    log_requests=True,
)

os.environ["HOST"] = "127.0.0.1"
os.environ["PORT"] = "8000"

app = server.create_app()


def main():
    """Run the server."""
    print("Running server...")

    # Use import string for reload=True to work
    # PYTHONPATH is already set at module level above
    try:
        uvicorn.run(
            "examples.test_server.main:app",  # Import string required for reload
            host="127.0.0.1",
            port=8000,
            log_level="info",
            reload=True,
            reload_dirs=[str(runtime_dir)],  # Only watch runtime directory for changes
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()


# Create one more detailed test server.
# Create all the agents related cases to test with the new server
