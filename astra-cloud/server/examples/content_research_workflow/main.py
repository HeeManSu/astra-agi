"""
Content Research Workflow Server - Phase 1: Agents Only

This server demonstrates a complete research and content creation workflow using 5 specialized AI agents.

Phase 1 Features:
- 5 specialized agents (Research, Writer, Editor, Fact-Checker, SEO Optimizer)
- Real tools implementation
- Memory and storage
- Streaming
- Code mode (SEO Optimizer)
- Middlewares and guardrails

No RAG or Teams in Phase 1.

Run with:
    cd packages/runtime
    uv run --package astra-runtime python examples/content_research_workflow/main.py

Or use VS Code debugger.


Access:
    - API Docs: http://127.0.0.1:8000/docs
    - Playground Agents: http://127.0.0.1:8000/api/v1/agents
    - Playground UI: http://127.0.0.1:8000/
"""


# PYTHONPATH Setup for Uvicorn Reload
#
# WHY THIS IS NEEDED:
# When using `uv run --package astra-runtime`, uv automatically resolves
# workspace dependencies for the main process. However, uvicorn's reload feature
# spawns a subprocess that needs to import "examples.content_research_workflow.main:app" as a module.
# The subprocess needs runtime_dir in PYTHONPATH to find the "examples" package.
#
# This is REQUIRED for uvicorn reload to work correctly, regardless of how
# we run the script (uv run or python directly).

import os
from pathlib import Path

from astra.server import AstraServer
from dotenv import load_dotenv
import uvicorn


load_dotenv()


current_dir = Path(__file__).parent
runtime_dir = current_dir.parent.parent

# Set PYTHONPATH environment variable for uvicorn reload subprocess
runtime_path = str(runtime_dir)
pythonpath = os.environ.get("PYTHONPATH", "")
if runtime_path not in pythonpath:
    os.environ["PYTHONPATH"] = f"{runtime_path}:{pythonpath}" if pythonpath else runtime_path


# Imports - uv run automatically resolves workspace dependencies
# These must come after PYTHONPATH setup for uvicorn reload to work


# Import agents from new structure
from examples.content_research_workflow.agents import (  # noqa: E402
    editor_agent,
    fact_checker_agent,
    research_agent,
    seo_optimizer_agent,
    writer_agent,
)


# Collect all agents
agents = [
    research_agent,
    writer_agent,
    editor_agent,
    fact_checker_agent,
    seo_optimizer_agent,
]

# Use shared storage from agents
storage = research_agent.storage

server = AstraServer(
    agents=agents,
    name="Content Research Workflow Server",
    version="1.0.0",
    description="Research and content creation workflow with specialized agents (Phase 1: Agents Only)",
    docs_enabled=True,
    storage=storage,
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

os.environ["HOST"] = os.getenv("HOST", "127.0.0.1")
os.environ["PORT"] = os.getenv("PORT", "8000")

app = server.create_app()


def main():
    try:
        uvicorn.run(
            "examples.content_research_workflow.main:app",
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
