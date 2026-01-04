"""
Advanced Astra Server Example.

Demonstrates:
- AstraServer class (advanced interface)
- Custom middleware
- Custom routes
- Startup/shutdown hooks
- Full configuration
- RuntimeContext usage

Run with:
    uvicorn examples.advanced_server_example:app --reload
"""

import logging
from typing import Any

from astra import Agent, HuggingFaceLocal, LibSQLStorage
from astra.server import AstraServer, ServerConfig
from fastapi import Request, Response


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Middleware
# ============================================================================


async def auth_middleware(request: Request, call_next) -> Response:
    """
    Example authentication middleware.

    In production, you would:
    - Check JWT tokens
    - Validate API keys
    - Set user context
    """
    # Example: Check for API key header
    api_key = request.headers.get("X-API-Key")

    # For demo, accept any key or no key
    if api_key:
        request.state.authenticated = True
        request.state.api_key = api_key
        logger.info(f"Authenticated request with API key: {api_key[:8]}...")
    else:
        request.state.authenticated = False

    response = await call_next(request)
    return response


async def timing_middleware(request: Request, call_next) -> Response:
    """Add X-Response-Time header."""
    import time

    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    return response


# ============================================================================
# Lifecycle Hooks
# ============================================================================


async def on_startup():
    """Called when server starts."""
    logger.info("🚀 Custom startup hook: Initializing resources...")
    # In production:
    # - Connect to external services
    # - Load ML models
    # - Initialize caches
    logger.info("✅ Custom startup complete")


async def on_shutdown():
    """Called when server shuts down."""
    logger.info("👋 Custom shutdown hook: Cleaning up...")
    # In production:
    # - Close connections
    # - Flush caches
    # - Save state
    logger.info("✅ Custom shutdown complete")


# ============================================================================
# Custom Routes
# ============================================================================


async def version_handler() -> dict[str, Any]:
    """Custom version endpoint."""
    return {
        "version": "2.0.0",
        "build": "2024.01.04",
        "python": "3.12",
    }


async def stats_handler() -> dict[str, Any]:
    """Custom stats endpoint."""
    return {
        "requests_today": 1234,
        "active_sessions": 42,
        "uptime_hours": 168,
    }


# ============================================================================
# Agents Setup
# ============================================================================

# Shared storage for all agents
storage = LibSQLStorage(
    url="file:./astra_demo.db",
    # In production use remote:
    # url="libsql://your-db.turso.io",
    # auth_token="your-token",
)

# Main assistant agent
assistant = Agent(
    name="assistant",
    model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
    instructions="""You are a helpful AI assistant.

You have access to the user's context which may include:
- user_id: The current user's ID
- channel: The communication channel (web, slack, discord)
- metadata: Additional context

Use this information to personalize your responses.""",
    storage=storage,
)

# Code review agent
code_reviewer = Agent(
    name="code-reviewer",
    model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
    instructions="""You are a code review specialist.

Review code for:
- Bugs and errors
- Performance issues
- Security vulnerabilities
- Best practices""",
    storage=storage,  # Shared storage
)


# ============================================================================
# Server Configuration
# ============================================================================

config = ServerConfig(
    name="Astra Advanced Demo",
    version="2.0.0",
    description="Advanced Astra Server with all features enabled",
    docs_enabled=True,
    cors_origins=["http://localhost:3000", "https://myapp.com"],
    cors_allow_credentials=True,
    log_requests=True,
    debug=True,
)


# ============================================================================
# Server Setup
# ============================================================================

# Create server with advanced interface
server = AstraServer(
    agents={
        "assistant": assistant,
        "code-reviewer": code_reviewer,
    },
    storage=storage,
    config=config,
)

# Add custom middleware (order matters - first added = outermost)
server.add_middleware(timing_middleware)
server.add_middleware(auth_middleware)

# Add custom routes
server.add_route("/version", version_handler, methods=["GET"])
server.add_route("/stats", stats_handler, methods=["GET"])

# Add lifecycle hooks
server.on_startup(on_startup)
server.on_shutdown(on_shutdown)

# Create the app
app = server.create_app()


# ============================================================================
# Usage Examples (via curl)
# ============================================================================

"""
# Health check
curl http://localhost:8000/health

# Server metadata
curl http://localhost:8000/v1/meta

# List agents
curl http://localhost:8000/v1/agents

# Custom version route
curl http://localhost:8000/version

# Custom stats route
curl http://localhost:8000/stats

# Generate with context (RuntimeContext)
curl -X POST http://localhost:8000/v1/agents/assistant/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-key" \
  -d '{
    "message": "Hello, who am I?",
    "context": {
      "user_id": "user-123",
      "channel": "slack",
      "metadata": {
        "workspace": "acme-corp",
        "timezone": "UTC"
      }
    }
  }'

# Stream response
curl -X POST http://localhost:8000/v1/agents/assistant/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a short story"}'

# Create thread
curl -X POST http://localhost:8000/v1/threads \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "assistant"}'

# Use thread in conversation  
curl -X POST http://localhost:8000/v1/agents/assistant/generate \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Remember me?",
    "thread_id": "YOUR-THREAD-ID"
  }'
"""


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
