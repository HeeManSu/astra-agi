"""
Astra Server Module.

Provides helper functions and classes to create FastAPI servers from Astra agents.

Example (Simple):
    from astra import Agent, Gemini
    from astra.server import create_app

    agent = Agent(
        name="assistant",
        model=Gemini(model="gemini-2.0-flash"),
        instructions="You are a helpful assistant.",
    )

    app = create_app(
        agents={"assistant": agent},
        cors_origins=["*"],
    )

    # Run with: uvicorn main:app

Example (Advanced):
    from astra.server import AstraServer, ServerConfig

    server = AstraServer(
        agents={"assistant": agent},
        config=ServerConfig(name="My API", docs_enabled=True),
    )
    server.add_middleware(auth_middleware)
    server.on_startup(my_startup_hook)
    app = server.create_app()
"""

from astra.server.app import AstraServer, create_app
from astra.server.config import ServerConfig
from astra.server.lifecycle import LifecycleError, MCPConnectionError, StorageConnectionError
from astra.server.registry import AgentRegistry, StorageInfo, create_registry


__all__ = [
    "AgentRegistry",
    "AstraServer",
    "LifecycleError",
    "MCPConnectionError",
    "ServerConfig",
    "StorageConnectionError",
    "StorageInfo",
    "create_app",
    "create_registry",
]
