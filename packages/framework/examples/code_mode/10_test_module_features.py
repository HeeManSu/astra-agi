"""
Test Example 10: Module Features (Explicit Module & Warnings)

Tests for:
- Explicit module parameter in @tool decorator
- Module inference from dot notation
- Warning when falling back to default module
- Explicit module overriding name inference
"""

import asyncio
import os
import sys


# Add framework src to path
src_path = os.path.join(os.path.dirname(__file__), "../../src")
sys.path.insert(0, src_path)

# Import framework components
try:
    from framework.agents import Agent
    from framework.agents.tool import tool
    from framework.models import Gemini
except ImportError as e:
    print("=" * 60)
    print("IMPORT ERROR: Framework dependencies not available")
    print("=" * 60)
    print(f"Error: {e}")
    print("\nTo run these tests:")
    print("  From workspace root:")
    print("    uv run python packages/framework/examples/code_mode/10_test_module_features.py")
    sys.exit(1)


async def test_explicit_module_parameter():
    """Test explicit module parameter."""
    print("=" * 60)
    print("TEST: Explicit Module Parameter")
    print("=" * 60)

    @tool(module="math")
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @tool(module="crm")
    def get_user(user_id: int) -> dict:
        """Get user."""
        return {"id": user_id}

    agent = Agent(
        name="ExplicitModuleAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent",
        tools=[add, get_user],
        code_mode=True,
    )

    await agent.invoke("Hello")

    grouped = agent.tool_registry.get_specs_grouped_by_module()

    assert "math" in grouped, "Should have 'math' module from explicit parameter"
    assert "crm" in grouped, "Should have 'crm' module from explicit parameter"

    math_tools = [t.name for t in grouped["math"]]
    crm_tools = [t.name for t in grouped["crm"]]

    assert "add" in math_tools, "add should be in math module"
    assert "get_user" in crm_tools, "get_user should be in crm module"

    print("✓ Explicit module parameter works correctly")
    print(f"  - Modules: {list(grouped.keys())}")
    for module, tools in grouped.items():
        print(f"    - {module}: {[t.name for t in tools]}")


async def test_module_inference_from_name():
    """Test module inference from dot notation in tool name."""
    print("\n" + "=" * 60)
    print("TEST: Module Inference from Name")
    print("=" * 60)

    @tool(name="crm.get_user")
    def get_user(user_id: int) -> dict:
        """Get user."""
        return {"id": user_id}

    @tool(name="gdrive.get_document")
    def get_doc(doc_id: str) -> dict:
        """Get document."""
        return {"id": doc_id}

    agent = Agent(
        name="InferenceAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent",
        tools=[get_user, get_doc],
        code_mode=True,
    )

    await agent.invoke("Hello")

    grouped = agent.tool_registry.get_specs_grouped_by_module()

    assert "crm" in grouped, "Should infer 'crm' from 'crm.get_user'"
    assert "gdrive" in grouped, "Should infer 'gdrive' from 'gdrive.get_document'"

    print("✓ Module inference from name works correctly")
    print(f"  - Modules: {list(grouped.keys())}")


async def test_explicit_overrides_inference():
    """Test that explicit module parameter overrides name inference."""
    print("\n" + "=" * 60)
    print("TEST: Explicit Module Overrides Inference")
    print("=" * 60)

    # Tool name suggests 'salesforce' module, but explicit module is 'crm'
    @tool(name="salesforce.get_account", module="crm")
    def get_account(account_id: str) -> dict:
        """Get account."""
        return {"id": account_id}

    agent = Agent(
        name="OverrideAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent",
        tools=[get_account],
        code_mode=True,
    )

    await agent.invoke("Hello")

    grouped = agent.tool_registry.get_specs_grouped_by_module()

    # Should be in 'crm' module (explicit), not 'salesforce' (from name)
    assert "crm" in grouped, "Should use explicit 'crm' module"
    assert "salesforce" not in grouped, "Should NOT use 'salesforce' from name"

    crm_tools = [t.name for t in grouped["crm"]]
    assert "salesforce.get_account" in crm_tools, "Tool should be in crm module despite name"

    print("✓ Explicit module overrides name inference")
    print(
        f"  - Tool 'salesforce.get_account' is in module: {[m for m, tools in grouped.items() if any(t.name == 'salesforce.get_account' for t in tools)]}"
    )


async def test_default_module_fallback():
    """Test that tools without explicit module or dots fall back to default."""
    print("\n" + "=" * 60)
    print("TEST: Default Module Fallback")
    print("=" * 60)

    # Tool without explicit module and without dots in name
    @tool
    def simple_tool(x: int) -> int:
        """Simple tool."""
        return x * 2

    agent = Agent(
        name="DefaultModuleAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="Test agent",
        tools=[simple_tool],
        code_mode=True,
    )

    await agent.invoke("Hello")

    grouped = agent.tool_registry.get_specs_grouped_by_module()

    # Should fall back to 'default' module
    assert "default" in grouped, (
        "Should have 'default' module for tool without explicit module or dots"
    )

    default_tools = [t.name for t in grouped["default"]]
    assert "simple_tool" in default_tools, "simple_tool should be in default module"

    print("✓ Default module fallback works correctly")
    print("  - Tool 'simple_tool' is in module: 'default'")
    print("  - Note: A warning should be logged about this fallback")


async def main():
    """Run all module feature tests."""
    print("\n" + "=" * 60)
    print("MODULE FEATURES TESTS")
    print("=" * 60)

    try:
        await test_explicit_module_parameter()
        await test_module_inference_from_name()
        await test_explicit_overrides_inference()
        await test_default_module_fallback()

        print("\n" + "=" * 60)
        print("✓ ALL MODULE FEATURE TESTS PASSED")
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
