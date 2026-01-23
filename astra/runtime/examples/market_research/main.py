"""
Market Research Server.

Run with: uvicorn main:app --reload
"""

import os
import sys

from dotenv import load_dotenv
from framework.storage.client import StorageClient
from framework.storage.databases.mongodb import MongoDBStorage
from runtime import AstraServer, TelemetryConfig


# Load .env from project root BEFORE any framework imports
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env"))
load_dotenv(env_path, override=True)

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from agent import market_research_agent


# Create Server
server = AstraServer(
    name="Market Research Server",
    agents=[market_research_agent],
    description="SellerGeni Market Research Agent powered by Astra.",
    storage=StorageClient(
        storage=MongoDBStorage("mongodb://localhost:27017", "market_research_agent")
    ),
    cors_allowed_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    # Auth enabled by default (requires ASTRA_JWT_SECRET env var)
    telemetry=TelemetryConfig(
        enabled=True,
        db_path="./market_obs.db",
    ),
)

# Expose App
app = server.get_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
