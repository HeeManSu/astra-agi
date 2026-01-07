"""
Test Server for Playground API Testing

This server creates multiple test agents for testing and debugging
the Astra Playground API endpoints, especially `/api/playground/agents`.

Run with:
    python examples/test_server/main.py

Or use VS Code debugger with "Python: Test Server - Playground API" configuration.

Access:
    - API Docs: http://127.0.0.1:8000/docs
    - Playground Agents: http://127.0.0.1:8000/api/playground/agents
    - Playground UI: http://127.0.0.1:8000/
"""

import os
from pathlib import Path
import sys


# Load environment variables from .env file (if present)
# Looks for .env in current directory and parent directories
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

# Add framework and runtime src to path to use inbuilt packages
current_dir = Path(__file__).parent
runtime_dir = current_dir.parent.parent
framework_dir = runtime_dir.parent / "framework"
workspace_root = runtime_dir.parent.parent

# Add paths in order of priority (local packages first)
sys.path.insert(0, str(framework_dir / "src"))
sys.path.insert(0, str(runtime_dir / "src"))
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(runtime_dir / "examples"))

# Set PYTHONPATH environment variable for uvicorn reload subprocess
# This must be done at module level, before any imports that uvicorn reload will use
# For "examples.test_server.main:app" to work, we need runtime_dir in PYTHONPATH
# (not just examples_dir), so Python can import "examples" as a package
runtime_path = str(runtime_dir)
pythonpath = os.environ.get("PYTHONPATH", "")
if runtime_path not in pythonpath:
    os.environ["PYTHONPATH"] = f"{runtime_path}:{pythonpath}" if pythonpath else runtime_path

from astra.server import AstraServer
from framework.agents.agent import Agent
from framework.agents.tool import tool
from framework.models.aws.bedrock import Bedrock
from framework.models.google.gemini import Gemini
from framework.storage.databases.mongodb import MongoDBStorage
import uvicorn


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
    model=Gemini("gemini-2.5-flash"),
    instructions="You are a helpful assistant that provides clear and concise answers.",
    description="A simple assistant agent with no tools or storage",
)

agent2 = Agent(
    name="Agent 2",
    id="agent-2",
    model=Gemini("gemini-2.5-flash"),
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
    model=Gemini("gemini-2.5-flash"),
    instructions="You are a helpful assistant that can perform calculations and get weather information.",
    description="An agent with multiple tools for testing",
    tools=[calculator, get_weather],
    storage=mongo_storage,
)

print("Creating agent 4...")
agent4 = Agent(
    name="Agent 4",
    id="agent-4",
    model=Bedrock(
        model_id="apac.amazon.nova-pro-v1:0",
        aws_region="ap-south-1",
    ),
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
