"""
Test Example 7: Tool Registry Unit Tests

Comprehensive unit tests for ToolRegistry covering:
- Tool registration (Python and MCP)
- Tool retrieval
- Tool listing and filtering
- Module grouping
- Edge cases (duplicates, empty registry, etc.)

NOTE: This test requires framework dependencies to be installed.
Run from workspace root with: uv run python packages/framework/examples/code_mode/07_test_tool_registry_unit.py
Or from packages/framework: uv run python examples/code_mode/07_test_tool_registry_unit.py
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
    from framework.agents.tool import Tool
    from framework.code_mode.tool_registry import ToolRegistry, ToolSpec
except ImportError as e:
    print("=" * 60)
    print("IMPORT ERROR: Framework dependencies not available")
    print("=" * 60)
    print(f"Error: {e}")
    print("\nTo run these tests:")
    print("  From workspace root:")
    print("    uv run python packages/framework/examples/code_mode/07_test_tool_registry_unit.py")
    print("  Or from packages/framework:")
    print("    uv run python examples/code_mode/07_test_tool_registry_unit.py")
    print(
        "\nNote: Use 'uv run' to ensure workspace dependencies (observability, memorybase) are available."
    )
    sys.exit(1)


# Test fixtures
def create_python_tool():
    """Create a sample Python tool."""

    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    return Tool(name="add", description="Add two numbers", func=add)


def create_mcp_tool():
    """Create a sample MCP tool."""

    async def get_document(doc_id: str):
        """Get a document."""
        return {"id": doc_id, "content": "test"}

    return Tool(name="gdrive.get_document", description="Get a document", func=get_document)


async def test_tool_spec():
    """Test ToolSpec dataclass."""
    print("=" * 60)
    print("TEST: ToolSpec Creation")
    print("=" * 60)

    python_tool = create_python_tool()
    spec = ToolSpec.from_tool(python_tool, module="math", is_mcp=False)  # type: ignore[arg-type]

    assert spec.name == "add"
    assert spec.description == "Add two numbers"
    assert spec.module == "math"
    assert spec.is_mcp is False
    assert spec.mcp_server_name is None
    print("✓ ToolSpec from Python tool: PASSED")

    mcp_tool = create_mcp_tool()
    spec = ToolSpec.from_tool(  # type: ignore[arg-type]
        mcp_tool, module="gdrive", is_mcp=True, mcp_server_name="gdrive-server"
    )

    assert spec.name == "gdrive.get_document"
    assert spec.module == "gdrive"
    assert spec.is_mcp is True
    assert spec.mcp_server_name == "gdrive-server"
    print("✓ ToolSpec from MCP tool: PASSED")


async def test_registration():
    """Test tool registration functionality."""
    print("\n" + "=" * 60)
    print("TEST: Tool Registration")
    print("=" * 60)

    registry = ToolRegistry(agent_id="test-agent")
    python_tool = create_python_tool()
    mcp_tool = create_mcp_tool()

    # Test registering Python tool
    spec = ToolSpec.from_tool(python_tool, module="math")  # type: ignore[arg-type]
    registry.register(spec)
    assert len(registry) == 1
    assert registry.has_tool("add")
    assert registry.get("add") == spec
    print("✓ Register Python tool: PASSED")

    # Test registering MCP tool
    spec2 = ToolSpec.from_tool(mcp_tool, module="gdrive", is_mcp=True, mcp_server_name="gdrive")  # type: ignore[arg-type]
    registry.register(spec2)
    assert len(registry) == 2
    assert registry.has_tool("gdrive.get_document")
    print("✓ Register MCP tool: PASSED")

    # Test duplicate registration raises error
    registry2 = ToolRegistry(agent_id="test-agent-2")
    spec3 = ToolSpec.from_tool(python_tool, module="math")  # type: ignore[arg-type]
    registry2.register(spec3)
    try:
        spec3_dup = ToolSpec.from_tool(python_tool, module="math")  # type: ignore[arg-type]
        registry2.register(spec3_dup)
        print("✗ Duplicate registration: FAILED (should raise ValueError)")
    except ValueError:
        print("✓ Duplicate registration raises ValueError: PASSED")

    # Test register_many
    registry3 = ToolRegistry(agent_id="test-agent-3")
    spec4 = ToolSpec.from_tool(python_tool, module="math")  # type: ignore[arg-type]
    spec5 = ToolSpec.from_tool(mcp_tool, module="gdrive", is_mcp=True)  # type: ignore[arg-type]
    registry3.register_many([spec4, spec5])
    assert len(registry3) == 2
    print("✓ Register many tools: PASSED")


async def test_retrieval():
    """Test tool retrieval functionality."""
    print("\n" + "=" * 60)
    print("TEST: Tool Retrieval")
    print("=" * 60)

    registry = ToolRegistry(agent_id="test-agent")
    python_tool = create_python_tool()
    spec = ToolSpec.from_tool(python_tool, module="math")  # type: ignore[arg-type]
    registry.register(spec)

    # Test get existing tool
    retrieved = registry.get("add")
    assert retrieved is not None
    assert retrieved.name == "add"
    print("✓ Get existing tool: PASSED")

    # Test get non-existent tool
    assert registry.get("nonexistent") is None
    print("✓ Get non-existent tool returns None: PASSED")

    # Test has_tool
    assert registry.has_tool("add") is True
    assert registry.has_tool("nonexistent") is False
    print("✓ has_tool method: PASSED")

    # Test __contains__ operator
    assert "add" in registry
    assert "nonexistent" not in registry
    print("✓ __contains__ operator: PASSED")


async def test_listing():
    """Test tool listing functionality."""
    print("\n" + "=" * 60)
    print("TEST: Tool Listing")
    print("=" * 60)

    registry = ToolRegistry(agent_id="test-agent")

    # Test empty registry
    assert registry.list_tools() == []
    assert registry.list_tool_names() == []
    print("✓ List empty registry: PASSED")

    # Test listing tools
    python_tool = create_python_tool()
    mcp_tool = create_mcp_tool()
    spec1 = ToolSpec.from_tool(python_tool, module="math")  # type: ignore[arg-type]
    spec2 = ToolSpec.from_tool(mcp_tool, module="gdrive", is_mcp=True)  # type: ignore[arg-type]

    registry.register(spec1)
    registry.register(spec2)

    tools = registry.list_tools()
    assert len(tools) == 2
    assert spec1 in tools
    assert spec2 in tools
    print("✓ List all tools: PASSED")

    names = registry.list_tool_names()
    assert len(names) == 2
    assert "add" in names
    assert "gdrive.get_document" in names
    print("✓ List tool names: PASSED")


async def test_filtering():
    """Test tool filtering by type."""
    print("\n" + "=" * 60)
    print("TEST: Tool Filtering")
    print("=" * 60)

    registry = ToolRegistry(agent_id="test-agent")
    python_tool = create_python_tool()
    mcp_tool = create_mcp_tool()

    spec1 = ToolSpec.from_tool(python_tool, module="math")  # type: ignore[arg-type]
    spec2 = ToolSpec.from_tool(mcp_tool, module="gdrive", is_mcp=True)  # type: ignore[arg-type]

    registry.register(spec1)
    registry.register(spec2)

    # Test Python tools filter
    python_tools = registry.get_python_tools()
    assert len(python_tools) == 1
    assert python_tools[0] == spec1
    assert python_tools[0].is_mcp is False
    print("✓ Filter Python tools: PASSED")

    # Test MCP tools filter
    mcp_tools = registry.get_mcp_tools()
    assert len(mcp_tools) == 1
    assert mcp_tools[0] == spec2
    assert mcp_tools[0].is_mcp is True
    print("✓ Filter MCP tools: PASSED")


async def test_module_grouping():
    """Test module grouping functionality."""
    print("\n" + "=" * 60)
    print("TEST: Module Grouping")
    print("=" * 60)

    registry = ToolRegistry(agent_id="test-agent")

    # Create multiple tools
    python_tool = create_python_tool()
    mcp_tool = create_mcp_tool()

    spec1 = ToolSpec.from_tool(python_tool, module="math")  # type: ignore[arg-type]

    def multiply(a: int, b: int) -> int:
        return a * b

    multiply_tool = Tool(name="multiply", description="Multiply two numbers", func=multiply)
    spec2 = ToolSpec.from_tool(multiply_tool, module="math")  # type: ignore[arg-type]
    spec3 = ToolSpec.from_tool(mcp_tool, module="gdrive", is_mcp=True)  # type: ignore[arg-type]

    registry.register(spec1)
    registry.register(spec2)
    registry.register(spec3)

    # Test get_by_module
    math_tools = registry.get_by_module("math")
    assert len(math_tools) == 2
    assert spec1 in math_tools
    assert spec2 in math_tools
    print("✓ Get tools by module: PASSED")

    empty_tools = registry.get_by_module("nonexistent")
    assert len(empty_tools) == 0
    print("✓ Get non-existent module returns empty: PASSED")

    # Test grouping
    grouped = registry.get_specs_grouped_by_module()
    assert "math" in grouped
    assert "gdrive" in grouped
    assert len(grouped["math"]) == 2
    assert len(grouped["gdrive"]) == 1
    assert spec1 in grouped["math"]
    assert spec2 in grouped["math"]
    assert spec3 in grouped["gdrive"]
    print("✓ Group tools by module: PASSED")


async def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 60)
    print("TEST: Edge Cases")
    print("=" * 60)

    registry = ToolRegistry(agent_id="test-agent")

    # Test empty registry
    assert len(registry) == 0
    assert registry.list_tools() == []
    assert registry.get("any") is None
    assert registry.has_tool("any") is False
    print("✓ Empty registry operations: PASSED")

    # Test clear
    python_tool = create_python_tool()
    spec = ToolSpec.from_tool(python_tool, module="math")  # type: ignore[arg-type]
    registry.register(spec)
    assert len(registry) == 1
    registry.clear()
    assert len(registry) == 0
    assert registry.get("add") is None
    print("✓ Clear registry: PASSED")

    # Test __len__
    registry2 = ToolRegistry(agent_id="test-agent-2")
    assert len(registry2) == 0
    python_tool = create_python_tool()
    spec = ToolSpec.from_tool(python_tool, module="math")  # type: ignore[arg-type]
    registry2.register(spec)
    assert len(registry2) == 1
    print("✓ __len__ operator: PASSED")

    # Test __repr__
    repr_str = repr(registry2)
    assert "ToolRegistry" in repr_str
    assert "test-agent-2" in repr_str
    assert "1" in repr_str
    print("✓ __repr__ method: PASSED")

    # Test default module
    registry3 = ToolRegistry(agent_id="test-agent-3")
    python_tool = create_python_tool()
    spec = ToolSpec.from_tool(python_tool, module="default")  # type: ignore[arg-type]
    registry3.register(spec)
    default_tools = registry3.get_by_module("default")
    assert len(default_tools) == 1
    print("✓ Default module handling: PASSED")

    # Test multiple modules
    registry4 = ToolRegistry(agent_id="test-agent-4")
    modules = ["crm", "gdrive", "salesforce", "math"]
    for i, module in enumerate(modules):

        def make_func(idx):
            def func(x: int) -> int:
                return idx

            return func

        tool = Tool(name=f"{module}.tool{i}", description=f"Tool {i}", func=make_func(i))
        spec = ToolSpec.from_tool(tool, module=module)  # type: ignore[arg-type]
        registry4.register(spec)

    grouped = registry4.get_specs_grouped_by_module()
    assert len(grouped) == 4
    for module in modules:
        assert module in grouped
        assert len(grouped[module]) == 1
    print("✓ Multiple modules: PASSED")


async def main():
    """Run all unit tests."""
    print("\n" + "=" * 60)
    print("TOOL REGISTRY UNIT TESTS")
    print("=" * 60)

    try:
        await test_tool_spec()
        await test_registration()
        await test_retrieval()
        await test_listing()
        await test_filtering()
        await test_module_grouping()
        await test_edge_cases()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
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
