"""
Test Playground Authentication Example

This example demonstrates:
- Team-scoped authentication with email/password
- Cookie-based JWT sessions
- Mastra-style jwt_secret configuration

Run with:
    ASTRA_JWT_SECRET=<your-secret> uv run --active python -m packages.runtime.examples.test_examples.auth_example

Or generate a secret:
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
"""

import os

from astra import Agent, HuggingFaceLocal
from astra.server import ServerConfig, create_app
from framework.storage.databases.libsql import LibSQLStorage


# Simple agent for testing
agent = Agent(
    name="test-agent",
    model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
    instructions="You are a helpful assistant.",
)

# Configure storage (required for auth)
storage = LibSQLStorage(url="sqlite+aiosqlite:///test_auth.db")
agent.storage = storage

# Create server config with Mastra-style jwt_secret
# Priority: config.jwt_secret > ASTRA_JWT_SECRET env var
config = ServerConfig(
    name="Auth Test Server",
    debug=True,
    cors_origins=["*"],
    playground_enabled=True,
    # jwt_secret will fall back to ASTRA_JWT_SECRET env var if not set here
)

# Create app
app = create_app(
    agents={"test-agent": agent},
    config=config,
    storage=storage,
)


if __name__ == "__main__":
    import uvicorn

    jwt_secret = os.getenv("ASTRA_JWT_SECRET")

    if not jwt_secret:
        print("❌ ERROR: ASTRA_JWT_SECRET not set!")
        print("\nTo fix:")
        print("1. Generate a secret:")
        print('   python3 -c "import secrets; print(secrets.token_urlsafe(32))"')
        print("\n2. Run with the secret:")
        print(
            "   ASTRA_JWT_SECRET=<paste-secret> uv run --active python -m packages.runtime.examples.test_examples.auth_example"
        )
        exit(1)

    print("✅ Starting server with authentication enabled")
    print(f"📝 JWT Secret: {jwt_secret[:10]}...")
    print("\n🌐 Open: http://localhost:8000")
    print("   → You'll see the login/signup page")
    print("   → First time: Create team account")
    print("   → Next times: Sign in with email/password")
    print("\n📚 API Docs: http://localhost:8000/docs")
    print("\nPress CTRL+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
