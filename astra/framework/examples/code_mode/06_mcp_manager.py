"""
Example 6: MCP Manager (Multiple Servers)

Demonstrates Tool Registry with MCPManager managing multiple MCP servers.
This shows how to use MCPManager to orchestrate multiple MCP servers at once.
"""

import asyncio
import os
import sys


# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from framework.agents import Agent
from framework.agents.tool import tool
from framework.mcp import MCPManager
from framework.models import Gemini


# Add a Python tool for comparison
@tool
def calculate_sum(numbers: list[int]) -> int:
    """Calculate the sum of a list of numbers."""
    return sum(numbers)


async def main():
    # Create MCPManager
    manager = MCPManager()

    # Add multiple MCP servers to the manager
    await manager.add_server("filesystem", {"path": "."})
    # Note: Add more servers if you have API keys
    # await manager.add_server("brave_search", {"api_key": "YOUR_API_KEY"})
    # await manager.add_server("github", {"api_key": "YOUR_GITHUB_TOKEN"})

    # Create agent with MCPManager and Python tool
    agent = Agent(
        name="MultiServerAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="You are a helpful assistant with access to multiple tools.",
        tools=[manager, calculate_sum],
        code_mode=True,
    )

    # Invoke agent (manager initializes all servers and tools populate registry)
    response = await agent.invoke("What tools do you have available?")
    print(f"Response: {response}\n")

    # Analyze tool registry
    print("=" * 60)
    print("TOOL REGISTRY ANALYSIS")
    print("=" * 60)

    print(f"\nTotal tools: {len(agent.tool_registry)}")

    # Filter by type
    python_tools = agent.tool_registry.get_python_tools()
    mcp_tools = agent.tool_registry.get_mcp_tools()

    print(f"\nPython tools ({len(python_tools)}):")
    for tool in python_tools:
        print(f"  - {tool.name}")

    print(f"\nMCP tools ({len(mcp_tools)}):")
    for tool in mcp_tools:
        server_info = (
            f"server: {tool.mcp_server_name}" if tool.mcp_server_name else "server: unknown"
        )
        print(f"  - {tool.name} ({server_info}, module: {tool.module})")

    # Group by module
    print("\nTools grouped by module:")
    grouped = agent.tool_registry.get_specs_grouped_by_module()
    for module, tools in grouped.items():
        print(f"\n  Module: {module} ({len(tools)} tools)")
        for tool in tools[:3]:  # Show first 3 tools per module
            tool_type = "MCP" if tool.is_mcp else "Python"
            print(f"    - {tool.name} ({tool_type})")
        if len(tools) > 3:
            print(f"    ... and {len(tools) - 3} more")

    # Note about MCPManager limitation
    print("\n" + "=" * 60)
    print("NOTE: MCPManager Limitation")
    print("=" * 60)
    print(
        "MCPManager aggregates tools from all servers but doesn't preserve\n"
        "which server each tool came from. That's why mcp_server_name is None\n"
        "for tools from MCPManager. Module names are inferred from tool names."
    )

    # Clean up
    await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
