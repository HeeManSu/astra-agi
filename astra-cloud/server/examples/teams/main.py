"""
Research Teams Server - Demonstrates Team functionality with SSE streaming.

Run with:
    cd packages/runtime
    uv run --package astra-runtime python examples/teams/main.py

Access:
    - API Docs: http://127.0.0.1:8000/docs
    - Teams: http://127.0.0.1:8000/api/v1/teams
    - Playground UI: http://127.0.0.1:8000/
"""

import os
from pathlib import Path

from astra.server import AstraServer
from dotenv import load_dotenv
from framework.storage.databases.mongodb import MongoDBStorage
import uvicorn


load_dotenv()


# Setup PYTHONPATH for imports
current_dir = Path(__file__).parent
runtime_dir = current_dir.parent.parent

runtime_path = str(runtime_dir)
pythonpath = os.environ.get("PYTHONPATH", "")
if runtime_path not in pythonpath:
    os.environ["PYTHONPATH"] = f"{runtime_path}:{pythonpath}" if pythonpath else runtime_path


# Import from local package using relative paths
from examples.teams.agents import (  # noqa: E402
    analyst_agent,
    researcher_agent,
    writer_agent,
)
from examples.teams.teams import research_team  # noqa: E402


# Collect all agents and teams
agents = [
    researcher_agent,
    analyst_agent,
    writer_agent,
]

teams = [
    research_team,
]


# Create storage for conversation persistence
storage = MongoDBStorage(
    url=os.getenv("MONGODB_URL", "mongodb://localhost:27017"),
    db_name="astra_teams",
)


# Create server with both agents and teams
server = AstraServer(
    agents=agents,
    teams=teams,
    storage=storage,
    name="Research Teams Server",
    version="1.0.0",
    description="Demonstrates Team functionality with SSE streaming",
    docs_enabled=True,
    playground_enabled=True,
    cors={
        "origins": [
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "*",
        ],
    },
    secret=os.getenv("ASTRA_JWT_SECRET", "dev-secret-for-testing"),
    debug_mode=True,
    log_requests=True,
)

# Runtime config
os.environ["HOST"] = os.getenv("HOST", "127.0.0.1")
os.environ["PORT"] = os.getenv("PORT", "8000")

# Create the FastAPI app
app = server.create_app()


def main():
    """Start the server."""
    try:
        uvicorn.run(
            "examples.teams.main:app",
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "8000")),
            log_level="info",
            reload=True,
            reload_dirs=[str(runtime_dir)],
        )
    except Exception as e:
        print(f"\nError starting server: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
