"""
Example 1: Python Tools Only

Demonstrates Tool Registry with Python @tool decorated functions.
"""

import asyncio
import os
import sys


# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from framework.agents import Agent
from framework.agents.tool import tool
from framework.models import Gemini


# Define Python tools
@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


@tool
def get_user(user_id: int) -> dict:
    """Get a user by ID."""
    return {"id": user_id, "name": "John Doe", "email": "john@example.com"}


async def main():
    # Create agent with Python tools
    agent = Agent(
        name="MathAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="You are a helpful math assistant.",
        tools=[add, multiply, get_user],
        code_mode=True,  # Enable code mode (default)
    )

    # Invoke agent (lazy initialization happens here)
    response = await agent.invoke("What is 5 + 3?")
    print(f"Response: {response}")

    # Check tool registry
    print(f"\nTotal tools: {len(agent.tool_registry)}")
    print(f"Tool names: {agent.tool_registry.list_tool_names()}")

    # Group by module
    grouped = agent.tool_registry.get_specs_grouped_by_module()
    print("\nTools grouped by module:")
    for module, tools in grouped.items():
        print(f"  {module}: {[t.name for t in tools]}")

    # Filter by type
    python_tools = agent.tool_registry.get_python_tools()
    mcp_tools = agent.tool_registry.get_mcp_tools()
    print(f"\nPython tools: {len(python_tools)}")
    print(f"MCP tools: {len(mcp_tools)}")


if __name__ == "__main__":
    asyncio.run(main())
