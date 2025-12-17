"""
Example 2: MCP Server Tools

Demonstrates Tool Registry with MCP server tools.
"""

import asyncio
import os
import sys


# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from framework.agents import Agent
from framework.mcp import MCPRegistry
from framework.models import Gemini


async def main():
    # Create MCP server
    fs_server = MCPRegistry.filesystem(path=".")

    # Create agent with MCP tools
    agent = Agent(
        name="FileAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="You are a helpful file management assistant.",
        tools=[fs_server],
        code_mode=True,
    )

    # Invoke agent (MCP server initializes and tools populate registry)
    response = await agent.invoke("List the files in the current directory")
    print(f"Response: {response}")

    # Check tool registry
    print(f"\nTotal tools: {len(agent.tool_registry)}")
    print(f"Tool names: {agent.tool_registry.list_tool_names()}")

    # Check MCP tools
    mcp_tools = agent.tool_registry.get_mcp_tools()
    print(f"\nMCP tools: {len(mcp_tools)}")
    for tool in mcp_tools:
        print(f"  - {tool.name} (server: {tool.mcp_server_name})")

    # Group by module
    grouped = agent.tool_registry.get_specs_grouped_by_module()
    print("\nTools grouped by module:")
    for module, tools in grouped.items():
        print(f"  {module}: {len(tools)} tools")


if __name__ == "__main__":
    asyncio.run(main())
