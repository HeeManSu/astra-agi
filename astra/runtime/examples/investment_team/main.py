"""
Astra Investment Team — Main Entry Point
-----------------------------------------

Multi-agent investment committee: 7 analysts, 1 team.

Run:
    cd astra/runtime
    uv run python -m examples.investment_team.main
"""

import os

from dotenv import load_dotenv


env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env"))
# Must load dotenv BEFORE importing agents so model classes get the right API keys
load_dotenv(env_path, override=True)

from framework.storage.client import StorageClient
from framework.storage.databases.mongodb import MongoDBStorage
from observability.storage.mongodb import TelemetryMongoDB
from runtime import AstraServer, TelemetryConfig

from .agents import ALL_AGENTS
from .teams import ALL_TEAMS


server = AstraServer(
    name="Astra Investment Team",
    agents=ALL_AGENTS,
    teams=ALL_TEAMS,
    description="$10M investment committee with 7 specialist analysts and 4 team modes",
    storage=StorageClient(storage=MongoDBStorage("mongodb://localhost:27017", "investment_team")),
    auth_enabled=False,
    cors_allowed_origins=[
        "http://localhost:3010",
        "http://127.0.0.1:3010",
        "http://localhost:3000",
    ],
    telemetry=TelemetryConfig(
        enabled=True,
        db_path=TelemetryMongoDB("mongodb://localhost:27017", "telemetry_investment_team"),
        debug=True,
    ),
)

app = server.get_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
