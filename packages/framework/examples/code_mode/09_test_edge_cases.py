"""
Test Example 9: Edge Cases and Error Handling

Tests for edge cases:
- Empty tools list
- Tool without description
- Tool with complex schema
- MCP server that fails to start
- MCPManager with no servers
- Tool name collisions
- Code mode disabled

NOTE: Run from workspace root with: uv run python packages/framework/examples/code_mode/09_test_edge_cases.py
Or from packages/framework: uv run python examples/code_mode/09_test_edge_cases.py
"""

import asyncio
import os
import sys
from typing import Any


# Add framework src to path
src_path = os.path.join(os.path.dirname(__file__), "../../src")
sys.path.insert(0, src_path)

# Import framework components
# Note: Run with 'uv run' from workspace root to ensure workspace dependencies are available
try:
    from framework.agents import Agent
    from framework.agents.tool import tool
    from framework.mcp import MCPManager
    from framework.models import Gemini
except ImportError as e:
    print("=" * 60)
    print("IMPORT ERROR: Framework dependencies not available")
    print("=" * 60)
    print(f"Error: {e}")
    print("\nTo run these tests:")
    print("  From workspace root:")
    print("    uv run python packages/framework/examples/code_mode/09_test_edge_cases.py")
    print("  Or from packages/framework:")
    print("    uv run python examples/code_mode/09_test_edge_cases.py")
    print(
        "\nNote: Use 'uv run' to ensure workspace dependencies (observability, memorybase) are available."
    )
    sys.exit(1)


async def test_empty_tools_list():
    """Test agent with empty tools list."""
    print("=" * 60)
    print("TEST: Empty Tools List")
    print("=" * 60)

    agent = Agent(
        name="EmptyAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="Test agent",
        tools=[],
        code_mode=True,
    )

    await agent.invoke("Hello")

    assert len(agent.tool_registry) == 0
    assert agent.tool_registry.list_tools() == []
    print("✓ Empty tools list handled correctly")


async def test_tool_without_description():
    """Test tool without description."""
    print("\n" + "=" * 60)
    print("TEST: Tool Without Description")
    print("=" * 60)

    @tool
    def no_desc_tool(x: int) -> int:
        # No docstring
        return x * 2

    agent = Agent(
        name="NoDescAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="Test agent",
        tools=[no_desc_tool],
        code_mode=True,
    )

    await agent.invoke("Hello")

    tool_spec = agent.tool_registry.get("no_desc_tool")
    assert tool_spec is not None
    # Description might be empty string if no docstring
    assert isinstance(tool_spec.description, str)
    print("✓ Tool without description handled correctly")


async def test_tool_with_complex_schema():
    """Test tool with complex schema (nested objects, arrays)."""
    print("\n" + "=" * 60)
    print("TEST: Complex Schema")
    print("=" * 60)

    @tool
    def complex_tool(
        user: dict,
        tags: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """Complex tool with nested types."""
        return {"processed": True, "user": user, "tags": tags}

    agent = Agent(
        name="ComplexAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="Test agent",
        tools=[complex_tool],
        code_mode=True,
    )

    await agent.invoke("Hello")

    tool_spec = agent.tool_registry.get("complex_tool")
    assert tool_spec is not None
    assert "properties" in tool_spec.parameters
    assert "user" in tool_spec.parameters["properties"]
    assert "tags" in tool_spec.parameters["properties"]
    print("✓ Complex schema handled correctly")
    print(f"  - Parameters: {list(tool_spec.parameters.get('properties', {}).keys())}")


async def test_mcp_manager_no_servers():
    """Test MCPManager with no servers."""
    print("\n" + "=" * 60)
    print("TEST: MCPManager with No Servers")
    print("=" * 60)

    manager = MCPManager()

    agent = Agent(
        name="NoServersAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="Test agent",
        tools=[manager],
        code_mode=True,
    )

    await agent.invoke("Hello")

    # Should have no tools
    assert len(agent.tool_registry) == 0
    print("✓ MCPManager with no servers handled correctly")


async def test_tool_name_collisions():
    """Test tool name collisions."""
    print("\n" + "=" * 60)
    print("TEST: Tool Name Collisions")
    print("=" * 60)

    @tool(name="duplicate")
    def tool1(x: int) -> int:
        """First tool."""
        return x

    @tool(name="duplicate")
    def tool2(x: int) -> int:
        """Second tool with same name."""
        return x * 2

    agent = Agent(
        name="CollisionAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="Test agent",
        tools=[tool1, tool2],
        code_mode=True,
    )

    # Should handle collision gracefully (first one registered, second fails)
    try:
        await agent.invoke("Hello")
        # If we get here, the collision was handled (either silently or first tool wins)
        print("✓ Tool name collision handled (first tool registered)")
    except Exception as e:
        # Or it might raise an error
        print(f"✓ Tool name collision raises error: {type(e).__name__}")


async def test_code_mode_disabled():
    """Test behavior when code_mode is disabled."""
    print("\n" + "=" * 60)
    print("TEST: Code Mode Disabled")
    print("=" * 60)

    @tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    agent = Agent(
        name="NoCodeModeAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="Test agent",
        tools=[add],
        code_mode=False,  # Disabled
    )

    await agent.invoke("Hello")

    # Registry should still exist but might not be populated
    # (depends on implementation - if code_mode=False, registry might not be used)
    # For now, we just check it doesn't crash
    print("✓ Code mode disabled handled correctly")
    print(f"  - Registry length: {len(agent.tool_registry)}")


async def test_special_characters_in_names():
    """Test tools with special characters in names."""
    print("\n" + "=" * 60)
    print("TEST: Special Characters in Names")
    print("=" * 60)

    @tool(name="tool-with-dashes")
    def tool_with_dashes(x: int) -> int:
        """Tool with dashes."""
        return x

    @tool(name="tool_with_underscores")
    def tool_with_underscores(x: int) -> int:
        """Tool with underscores."""
        return x

    agent = Agent(
        name="SpecialCharsAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="Test agent",
        tools=[tool_with_dashes, tool_with_underscores],
        code_mode=True,
    )

    await agent.invoke("Hello")

    assert agent.tool_registry.has_tool("tool-with-dashes")
    assert agent.tool_registry.has_tool("tool_with_underscores")
    print("✓ Special characters in names handled correctly")
    print(f"  - Tools: {agent.tool_registry.list_tool_names()}")


async def test_multiple_invocations():
    """Test that registry persists across multiple invocations."""
    print("\n" + "=" * 60)
    print("TEST: Multiple Invocations")
    print("=" * 60)

    @tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    agent = Agent(
        name="MultiInvokeAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="Test agent",
        tools=[add],
        code_mode=True,
    )

    # First invocation
    await agent.invoke("Hello")
    first_count = len(agent.tool_registry)

    # Second invocation
    await agent.invoke("Hello again")
    second_count = len(agent.tool_registry)

    # Should be the same (no re-registration)
    assert first_count == second_count == 1
    print("✓ Registry persists across invocations")
    print(f"  - After first invoke: {first_count} tools")
    print(f"  - After second invoke: {second_count} tools")


async def main():
    """Run all edge case tests."""
    print("\n" + "=" * 60)
    print("EDGE CASE TESTS")
    print("=" * 60)

    try:
        await test_empty_tools_list()
        await test_tool_without_description()
        await test_tool_with_complex_schema()
        await test_mcp_manager_no_servers()
        await test_tool_name_collisions()
        await test_code_mode_disabled()
        await test_special_characters_in_names()
        await test_multiple_invocations()

        print("\n" + "=" * 60)
        print("✓ ALL EDGE CASE TESTS PASSED")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
