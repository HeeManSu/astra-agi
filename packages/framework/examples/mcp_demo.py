"""
Example demonstrating MCP integration in Astra.

Shows filesystem, calculator, and web search MCP tools.
"""
import asyncio
from framework.agents import Agent
from framework.models import Gemini
from framework.mcp import MCPTools
from framework.mcp.builtin import FilesystemMCP, CalculatorMCP, WebSearchMCP


async def example_filesystem():
    """Example 1: Filesystem MCP tools."""
    print("=== Example 1: Filesystem MCP ===\n")
    
    mcp = FilesystemMCP.create(root_path=".", prefix="fs")
    
    agent = Agent(
        name="FileAgent",
        model=Gemini("1.5-flash"),
        instructions="You can read and write files using MCP tools.",
        tools=[mcp]
    )
    
    # MCP tools auto-initialize on first run
    response = await agent.invoke("List the files in the current directory")
    print(f"Response: {response['content'][:200]}...")
    print()


async def example_custom_mcp():
    """Example 2: Custom MCP server."""
    print("=== Example 2: Custom MCP Server ===\n")
    
    mcp = MCPTools(
        command="npx -y @modelcontextprotocol/server-filesystem /tmp",
        prefix="tmp"
    )
    
    agent = Agent(
        name="TmpAgent",
        model=Gemini("1.5-flash"),
        tools=[mcp]
    )
    
    response = await agent.invoke("What files are in /tmp?")
    print(f"Response: {response['content'][:200]}...")
    print()


async def example_multiple_mcp():
    """Example 3: Multiple MCP servers."""
    print("=== Example 3: Multiple MCP Servers ===\n")
    
    fs_mcp = FilesystemMCP.create(root_path=".")
    calc_mcp = CalculatorMCP.create()
    
    agent = Agent(
        name="MultiToolAgent",
        model=Gemini("1.5-flash"),
        instructions="You have access to filesystem and calculator tools.",
        tools=[fs_mcp, calc_mcp]
    )
    
    response = await agent.invoke("Calculate 25 * 4 and write the result to result.txt")
    print(f"Response: {response['content'][:200]}...")
    print()


async def example_collision_detection():
    """Example 4: Automatic collision detection."""
    print("=== Example 4: Collision Detection ===\n")
    
    # No prefix specified - will auto-detect collisions
    mcp1 = MCPTools(
        command="npx -y @modelcontextprotocol/server-filesystem .",
        name="fs1"
    )
    
    mcp2 = MCPTools(
        command="npx -y @modelcontextprotocol/server-filesystem /tmp",
        name="fs2"
    )
    
    agent = Agent(
        name="CollisionAgent",
        model=Gemini("1.5-flash"),
        tools=[mcp1, mcp2]
    )
    
    # Prefixes will be auto-added to avoid collisions
    response = await agent.invoke("List files from both directories")
    print(f"Response: {response['content'][:200]}...")
    print()


async def main():
    """Run all examples."""
    print("=" * 60)
    print("MCP Integration Examples")
    print("=" * 60)
    print()
    
    await example_filesystem()
    await example_custom_mcp()
    await example_multiple_mcp()
    await example_collision_detection()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
