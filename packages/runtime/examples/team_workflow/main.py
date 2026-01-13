"""
E-commerce Order Fulfillment Server - Production Example

Demonstrates all team execution modes with a realistic e-commerce order
fulfillment workflow.

Run with:
    cd packages/runtime
    uv run --package astra-runtime python examples/team_workflow/main.py

Access:
    - API Docs: http://127.0.0.1:8000/docs
    - Playground Teams: http://127.0.0.1:8000/api/v1/teams
    - Playground UI: http://127.0.0.1:8000/
"""


# PYTHONPATH Setup for Uvicorn Reload
#
# WHY THIS IS NEEDED:
# When using `uv run --package astra-runtime`, uv automatically resolves
# workspace dependencies for the main process. However, uvicorn's reload feature
# spawns a subprocess that needs to import "examples.team_workflow.main:app" as a module.
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


# Import agents from e-commerce order fulfillment structure
from examples.team_workflow.agents import (  # noqa: E402
    customer_service_agent,
    fraud_detection_agent,
    inventory_agent,
    order_validator_agent,
    payment_agent,
    shipping_agent,
)

# Import teams
from examples.team_workflow.teams import (  # noqa: E402
    customer_support_team,
    fraud_detection_team,
    operations_team,
    order_processing_team,
)


# Collect all agents
agents = [
    order_validator_agent,
    inventory_agent,
    payment_agent,
    shipping_agent,
    customer_service_agent,
    fraud_detection_agent,
]

# Collect all teams
teams = [
    order_processing_team,
    customer_support_team,
    fraud_detection_team,
    operations_team,
]

# Use shared storage from db
from examples.team_workflow.db import db  # noqa: E402


# SERVER INITIALIZATION
# NOTE ON "DOUBLE INITIALIZATION":
# If you run this script directly (python main.py) with `reload=True`, you will see
# the server initialize TWICE.
#
# 1. First Run (Main Process): The script runs top-to-bottom. The `server` and `app`
#    objects are created in the global scope so `if __name__ == "__main__":` can run.
#
# 2. Second Run (Uvicorn Worker): `uvicorn.run()` spawns a subprocess. This subprocess
#    imports this file as a module ("examples.team_workflow.main"). This import
#    executes the global scope *again* to create the `app` object that Uvicorn serves.
#
# This is normal, correct behavior for hot-reloading in Python.

server = AstraServer(
    agents=agents,
    teams=teams,
    name="E-commerce Order Fulfillment Server",
    version="1.0.0",
    description=(
        "Production example demonstrating all team execution modes with "
        "realistic e-commerce order fulfillment workflow "
        "(route, coordinate, collaborate, hierarchical)"
    ),
    docs_enabled=True,
    storage=db,
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

# Runtime config injection
os.environ["HOST"] = os.getenv("HOST", "127.0.0.1")
os.environ["PORT"] = os.getenv("PORT", "8000")

# Create the FastAPI app (This is what Uvicorn looks for)
app = server.create_app()


def main():
    try:
        # We use the import string "examples.team_workflow.main:app"
        # This tells uvicorn to import the module to find the app instance.
        uvicorn.run(
            "examples.team_workflow.main:app",
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
