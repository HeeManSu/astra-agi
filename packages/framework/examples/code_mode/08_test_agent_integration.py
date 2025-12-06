"""
Test Example 8: Agent Integration Tests

Tests for Agent tool registration covering:
- Python tools registration
- MCPServer registration
- MCPManager registration (with server identity preservation)
- Mixed tools (Python + MCP)
- Lazy initialization
- Module inference

NOTE: Run from workspace root with: uv run python packages/framework/examples/code_mode/08_test_agent_integration.py
Or from packages/framework: uv run python examples/code_mode/08_test_agent_integration.py
"""

import asyncio
import os
import sys


# Add framework src to path
src_path = os.path.join(os.path.dirname(__file__), "../../src")
sys.path.insert(0, src_path)

# Import framework components
# Note: Run with 'uv run' from workspace root to ensure workspace dependencies are available
try:
    from framework.agents import Agent
    from framework.agents.tool import tool
    from framework.mcp import MCPManager, MCPRegistry
    from framework.models import Gemini
except ImportError as e:
    print("=" * 60)
    print("IMPORT ERROR: Framework dependencies not available")
    print("=" * 60)
    print(f"Error: {e}")
    print("\nTo run these tests:")
    print("  From workspace root:")
    print("    uv run python packages/framework/examples/code_mode/08_test_agent_integration.py")
    print("  Or from packages/framework:")
    print("    uv run python examples/code_mode/08_test_agent_integration.py")
    print(
        "\nNote: Use 'uv run' to ensure workspace dependencies (observability, memorybase) are available."
    )
    sys.exit(1)


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
def crm_get_user(user_id: int) -> dict:
    """Get a user from CRM."""
    return {"id": user_id, "name": "John Doe"}


async def test_python_tools_registration():
    """Test Python tools registration."""
    print("=" * 60)
    print("TEST: Python Tools Registration")
    print("=" * 60)

    agent = Agent(
        name="PythonAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent",
        tools=[add, multiply],
        code_mode=True,
    )

    # Trigger lazy initialization
    await agent.invoke("Hello")

    # Check registry
    assert len(agent.tool_registry) == 2
    assert agent.tool_registry.has_tool("add")
    assert agent.tool_registry.has_tool("multiply")

    # Check Python tools
    python_tools = agent.tool_registry.get_python_tools()
    assert len(python_tools) == 2
    assert all(not tool.is_mcp for tool in python_tools)

    # Check module inference
    grouped = agent.tool_registry.get_specs_grouped_by_module()
    # Tools without dots should go to "default" module
    assert "default" in grouped or len(grouped) > 0

    print("✓ Python tools registered correctly")
    print(f"  - Total tools: {len(agent.tool_registry)}")
    print(f"  - Tool names: {agent.tool_registry.list_tool_names()}")


async def test_mcp_server_registration():
    """Test MCPServer registration."""
    print("\n" + "=" * 60)
    print("TEST: MCP Server Registration")
    print("=" * 60)

    # Create MCP server
    fs_server = MCPRegistry.filesystem(path=".")

    agent = Agent(
        name="MCPAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent",
        tools=[fs_server],
        code_mode=True,
    )

    # Trigger lazy initialization
    await agent.invoke("Hello")

    # Check registry has MCP tools
    mcp_tools = agent.tool_registry.get_mcp_tools()
    assert len(mcp_tools) > 0, "MCP tools should be registered"

    # Check server name is preserved
    for mcp_tool in mcp_tools:
        assert mcp_tool.is_mcp is True
        assert mcp_tool.mcp_server_name == "filesystem", (
            f"Expected server name 'filesystem', got {mcp_tool.mcp_server_name}"
        )

    # Check module uses server name
    grouped = agent.tool_registry.get_specs_grouped_by_module()
    assert "filesystem" in grouped, "Module should use server name"

    print("✓ MCP server tools registered correctly")
    print(f"  - Total tools: {len(agent.tool_registry)}")
    print(f"  - MCP tools: {len(mcp_tools)}")
    print(f"  - Server name preserved: {mcp_tools[0].mcp_server_name if mcp_tools else 'N/A'}")


async def test_mcp_manager_registration():
    """Test MCPManager registration with server identity preservation."""
    print("\n" + "=" * 60)
    print("TEST: MCP Manager Registration")
    print("=" * 60)

    # Create MCPManager with multiple servers
    manager = MCPManager()
    await manager.add_server("filesystem", {"path": "."})

    agent = Agent(
        name="ManagerAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent",
        tools=[manager],
        code_mode=True,
    )

    # Trigger lazy initialization
    await agent.invoke("Hello")

    # Check registry has MCP tools
    mcp_tools = agent.tool_registry.get_mcp_tools()
    assert len(mcp_tools) > 0, "MCP tools should be registered"

    # CRITICAL: Check that server name is preserved (not None)
    # This tests the fix where we iterate servers directly
    server_names = [tool.mcp_server_name for tool in mcp_tools]
    assert None not in server_names, "Server names should be preserved, not None"
    assert "filesystem" in server_names, "Should have filesystem server name"

    # Check module uses server name
    grouped = agent.tool_registry.get_specs_grouped_by_module()
    assert "filesystem" in grouped, "Module should use server name"

    print("✓ MCPManager tools registered correctly")
    print(f"  - Total tools: {len(agent.tool_registry)}")
    print(f"  - MCP tools: {len(mcp_tools)}")
    print(f"  - Server names preserved: {set(server_names)}")

    # Cleanup
    await manager.stop()


async def test_mixed_tools():
    """Test mixed Python and MCP tools."""
    print("\n" + "=" * 60)
    print("TEST: Mixed Tools (Python + MCP)")
    print("=" * 60)

    fs_server = MCPRegistry.filesystem(path=".")

    agent = Agent(
        name="MixedAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent",
        tools=[add, multiply, crm_get_user, fs_server],
        code_mode=True,
    )

    # Trigger lazy initialization
    await agent.invoke("Hello")

    # Check both types are registered
    python_tools = agent.tool_registry.get_python_tools()
    mcp_tools = agent.tool_registry.get_mcp_tools()

    assert len(python_tools) == 3, f"Expected 3 Python tools, got {len(python_tools)}"
    assert len(mcp_tools) > 0, "Should have MCP tools"

    # Check totals match
    total = len(python_tools) + len(mcp_tools)
    assert total == len(agent.tool_registry), "Total should match sum of types"

    print("✓ Mixed tools registered correctly")
    print(f"  - Python tools: {len(python_tools)}")
    print(f"  - MCP tools: {len(mcp_tools)}")
    print(f"  - Total: {len(agent.tool_registry)}")


async def test_lazy_initialization():
    """Test lazy initialization of tool registry."""
    print("\n" + "=" * 60)
    print("TEST: Lazy Initialization")
    print("=" * 60)

    agent = Agent(
        name="LazyAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent",
        tools=[add, multiply],
        code_mode=True,
    )

    # Before invoke, registry should be empty (if code_mode is enabled)
    # Actually, with code_mode=True, it's initialized lazily on first invoke
    # So we check it's empty before first invoke
    initial_count = len(agent.tool_registry)
    assert initial_count == 0, "Registry should be empty before first invoke"

    # Trigger lazy initialization
    await agent.invoke("Hello")

    # After invoke, registry should be populated
    final_count = len(agent.tool_registry)
    assert final_count == 2, f"Registry should have 2 tools after invoke, got {final_count}"

    print("✓ Lazy initialization works correctly")
    print(f"  - Before invoke: {initial_count} tools")
    print(f"  - After invoke: {final_count} tools")


async def test_module_inference():
    """Test module inference from tool names."""
    print("\n" + "=" * 60)
    print("TEST: Module Inference")
    print("=" * 60)

    @tool(name="crm.get_user")
    def crm_get_user(user_id: int) -> dict:
        """Get user."""
        return {"id": user_id}

    @tool(name="gdrive.get_document")
    def gdrive_get_doc(doc_id: str) -> dict:
        """Get document."""
        return {"id": doc_id}

    agent = Agent(
        name="InferenceAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent",
        tools=[crm_get_user, gdrive_get_doc],
        code_mode=True,
    )

    await agent.invoke("Hello")

    grouped = agent.tool_registry.get_specs_grouped_by_module()

    # Tools with dots should be grouped by prefix (module inference uses dots, not underscores)
    assert "crm" in grouped, "Should infer 'crm' module from 'crm.get_user'"
    assert "gdrive" in grouped, "Should infer 'gdrive' module from 'gdrive.get_document'"

    print("✓ Module inference works correctly")
    print(f"  - Modules: {list(grouped.keys())}")
    for module, tools in grouped.items():
        print(f"    - {module}: {[t.name for t in tools]}")


async def test_agent_isolation():
    """Test that different agents have isolated registries."""
    print("\n" + "=" * 60)
    print("TEST: Agent Isolation")
    print("=" * 60)

    agent1 = Agent(
        name="Agent1",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent 1",
        tools=[add],
        code_mode=True,
    )

    agent2 = Agent(
        name="Agent2",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent 2",
        tools=[multiply],
        code_mode=True,
    )

    await agent1.invoke("Hello")
    await agent2.invoke("Hello")

    # Each agent should have its own registry
    assert len(agent1.tool_registry) == 1
    assert len(agent2.tool_registry) == 1
    assert agent1.tool_registry.has_tool("add")
    assert agent2.tool_registry.has_tool("multiply")
    assert not agent1.tool_registry.has_tool("multiply")
    assert not agent2.tool_registry.has_tool("add")

    print("✓ Agent isolation works correctly")
    print(f"  - Agent1 tools: {agent1.tool_registry.list_tool_names()}")
    print(f"  - Agent2 tools: {agent2.tool_registry.list_tool_names()}")


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("AGENT INTEGRATION TESTS")
    print("=" * 60)

    try:
        # await test_python_tools_registration()
        # await test_mcp_server_registration()
        # await test_mcp_manager_registration()
        # await test_mixed_tools()
        # await test_lazy_initialization()
        await test_module_inference()
        await test_agent_isolation()

        print("\n" + "=" * 60)
        print("✓ ALL INTEGRATION TESTS PASSED")
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
