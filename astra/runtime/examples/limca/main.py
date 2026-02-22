"""Limca Server - Codebase Q/A Agent with Telemetry."""

import os
import sys

# CRITICAL: Load .env BEFORE any framework imports that might use API keys
from dotenv import load_dotenv


# Add paths before any framework imports
sys.path.insert(0, os.path.dirname(__file__))  # for local agent/tools imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../runtime/src")))

# Load env from project root - MUST happen before framework imports
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env"))
load_dotenv(env_path, override=True)

# NOW import framework modules (after env is loaded)
from framework.storage.client import StorageClient
from framework.storage.databases.mongodb import MongoDBStorage
from observability.storage.mongodb import TelemetryMongoDB

from astra.runtime.examples.limca.agent import limca_agent
from astra.runtime.src.runtime.server import AstraServer, TelemetryConfig


# Default codebase to index
# DEFAULT_CODEBASE = "https://github.com/agno-agi/agno"


server = AstraServer(
    name="Limca Codebase Server",
    agents=[limca_agent],
    description="A server hosting Limca - the codebase Q/A agent.",
    storage=StorageClient(storage=MongoDBStorage("mongodb://localhost:27017", "limca_db")),
    cors_allowed_origins=["http://localhost:3010", "http://127.0.0.1:3010"],
    auth_enabled=False,  # Disable auth for local development
    telemetry=TelemetryConfig(
        enabled=True,
        db_path=TelemetryMongoDB("mongodb://localhost:27017", "telemetry_limca"),
        debug=True,
    ),
)

app = server.get_app()

# Wiki routes removed - wiki generation is available via agent tools only

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
