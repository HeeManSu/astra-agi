import asyncio
import os
import sys


# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from framework.mcp import MCPManager
from framework.mcp.utils import TrackingAgent, log_to_csv
from framework.models.google.gemini import Gemini


async def main():
    # 1. Initialize Manager
    manager = MCPManager()

    print("--- Adding Filesystem MCP Server ---")
    await manager.add_server("filesystem", {"path": "."})

    print("--- Fetching Tools ---")
    try:
        tools = await manager.get_tools()
    except Exception as e:
        print(f"Failed to load tools: {e}")
        return

    print(f"Loaded {len(tools)} tools.")
    for i, t in enumerate(tools):
        print(f"Tool {i}: {t.name}")
        print(f"  Params: {t.parameters}")

    # 2. Create TrackingAgent
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n[WARN] GOOGLE_API_KEY not found.")
        return

    agent = TrackingAgent(
        name="SimpleFilesystemAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="You are a helpful assistant that can read files.",
        tools=tools,
    )

    print("\n--- Invoking Agent ---")
    try:
        response = await agent.invoke("List the files in the current directory.")
        print("\nResponse:")
        print(response)

        # 3. Log Usage
        log_to_csv(agent.name, agent.last_usage)

    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Agent invocation failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
