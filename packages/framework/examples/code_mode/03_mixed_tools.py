"""
Example 3: Mixed Tools (Python + MCP)

Demonstrates Tool Registry with both Python @tool functions and MCP server tools.
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


# Define Python tools
@tool
def calculate(a: int, b: int, operation: str) -> int:
    """Perform a calculation.

    Args:
        a: First number
        b: Second number
        operation: Operation to perform (add, subtract, multiply, divide)
    """
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        return a // b if b != 0 else 0
    return 0


@tool
def format_result(value: int, prefix: str = "Result") -> str:
    """Format a result with a prefix."""
    return f"{prefix}: {value}"


async def main():
    # Create MCP server
    fs_server = MCPRegistry.filesystem(path=".")

    # Create agent with mixed tools
    agent = Agent(
        name="HybridAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="You are a helpful assistant with calculation and file management capabilities.",
        tools=[calculate, format_result, fs_server],
        code_mode=True,
    )

    # Invoke agent
    response = await agent.invoke("Calculate 10 + 5 and format the result")
    print(f"Response: {response}")

    # Analyze tool registry
    print(f"\n{'=' * 50}")
    print("TOOL REGISTRY ANALYSIS")
    print(f"{'=' * 50}")

    print(f"\nTotal tools: {len(agent.tool_registry)}")

    # Filter by type
    python_tools = agent.tool_registry.get_python_tools()
    mcp_tools = agent.tool_registry.get_mcp_tools()

    print(f"\nPython tools ({len(python_tools)}):")
    for tool in python_tools:
        print(f"  - {tool.name} (module: {tool.module})")

    print(f"\nMCP tools ({len(mcp_tools)}):")
    for tool in mcp_tools:
        print(f"  - {tool.name} (server: {tool.mcp_server_name}, module: {tool.module})")

    # Group by module
    grouped = agent.tool_registry.get_specs_grouped_by_module()
    print("\nTools grouped by module:")
    for module, tools in grouped.items():
        print(f"  {module}:")
        for tool in tools:
            tool_type = "MCP" if tool.is_mcp else "Python"
            print(f"    - {tool.name} ({tool_type})")


if __name__ == "__main__":
    asyncio.run(main())
