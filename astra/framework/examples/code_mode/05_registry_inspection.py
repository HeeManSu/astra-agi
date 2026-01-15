"""
Example 5: Tool Registry Inspection

Demonstrates advanced Tool Registry inspection and querying.
"""

import asyncio
import os
import sys


# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from framework.agents import Agent
from framework.agents.tool import tool
from framework.mcp import MCPRegistry
from framework.models import Gemini


# Define tools with module namespaces
@tool
def crm_get_user(user_id: int) -> dict:
    """Get a user from CRM."""
    return {"id": user_id, "name": "John Doe"}


@tool
def crm_update_user(user_id: int, data: dict) -> dict:
    """Update a user in CRM."""
    return {"id": user_id, "updated": True}


@tool
def email_send(to: str, subject: str, body: str) -> bool:
    """Send an email."""
    return True


async def main():
    # Create MCP server
    fs_server = MCPRegistry.filesystem(path=".")

    # Create agent
    agent = Agent(
        name="InspectionAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="You are a helpful assistant.",
        tools=[crm_get_user, crm_update_user, email_send, fs_server],
        code_mode=True,
    )

    # Trigger lazy initialization
    await agent.invoke("Hello")

    print("=" * 60)
    print("TOOL REGISTRY INSPECTION")
    print("=" * 60)

    # Basic stats
    print(f"\nTotal tools: {len(agent.tool_registry)}")
    print(f"Tool names: {agent.tool_registry.list_tool_names()}")

    # Check specific tool
    print(f"\nHas 'crm_get_user': {agent.tool_registry.has_tool('crm_get_user')}")
    print(f"Has 'nonexistent': {agent.tool_registry.has_tool('nonexistent')}")

    # Get specific tool
    tool_spec = agent.tool_registry.get("crm_get_user")
    if tool_spec:
        print("\nTool details for 'crm_get_user':")
        print(f"  Name: {tool_spec.name}")
        print(f"  Description: {tool_spec.description}")
        print(f"  Module: {tool_spec.module}")
        print(f"  Is MCP: {tool_spec.is_mcp}")
        print(f"  Parameters: {list(tool_spec.parameters.get('properties', {}).keys())}")

    # Group by module
    print("\nTools grouped by module:")
    grouped = agent.tool_registry.get_specs_grouped_by_module()
    for module, tools in grouped.items():
        print(f"\n  Module: {module}")
        for tool in tools:
            tool_type = "MCP" if tool.is_mcp else "Python"
            print(f"    - {tool.name} ({tool_type})")

    # Filter by type
    print("\nPython tools:")
    for tool in agent.tool_registry.get_python_tools():
        print(f"  - {tool.name}")

    print("\nMCP tools:")
    for tool in agent.tool_registry.get_mcp_tools():
        print(f"  - {tool.name} (server: {tool.mcp_server_name})")

    # Get tools by module
    print("\nTools in 'default' module:")
    default_tools = agent.tool_registry.get_by_module("default")
    for tool in default_tools:
        print(f"  - {tool.name}")


if __name__ == "__main__":
    asyncio.run(main())
