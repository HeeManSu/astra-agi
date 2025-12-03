"""
Test script to verify MCP schema sanitization is working correctly.
"""

import asyncio
import os
import sys


# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from framework.mcp import MCPManager


async def test_schema_sanitization():
    """Test that MCP schemas are properly sanitized (no $schema fields)."""
    print("=" * 60)
    print("Testing MCP Schema Sanitization")
    print("=" * 60)

    manager = MCPManager()
    await manager.add_server("filesystem", {"path": "."})

    try:
        tools = await manager.get_tools()
        print(f"\n✓ Loaded {len(tools)} tools from MCP server")

        # Check each tool's schema for $schema fields
        issues_found = []
        for tool in tools:
            params = tool.parameters

            # Check top level
            if "$schema" in params:
                issues_found.append(f"Tool '{tool.name}': $schema found at top level")

            # Check nested properties
            if "properties" in params:
                for prop_name, prop_schema in params["properties"].items():
                    if isinstance(prop_schema, dict) and "$schema" in prop_schema:
                        issues_found.append(
                            f"Tool '{tool.name}': $schema found in property '{prop_name}'"
                        )

            # Check items
            if "items" in params:
                if isinstance(params["items"], dict) and "$schema" in params["items"]:
                    issues_found.append(f"Tool '{tool.name}': $schema found in items")

        if issues_found:
            print("\n✗ FAILED: Found $schema fields in schemas:")
            for issue in issues_found:
                print(f"  - {issue}")
            return False
        else:
            print("\n✓ PASSED: No $schema fields found in any tool schemas")
            print(f"✓ All {len(tools)} tools have sanitized schemas")

        # Show example schema structure
        if tools:
            example_tool = tools[0]
            print(f"\nExample schema structure for '{example_tool.name}':")
            print(f"  - Has 'type': {'type' in example_tool.parameters}")
            print(f"  - Has 'properties': {'properties' in example_tool.parameters}")
            print(f"  - No '$schema': {'$schema' not in example_tool.parameters}")

        return True

    except Exception as e:
        print(f"\n✗ FAILED: Error during test: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        await manager.stop()


async def main():
    """Run the schema sanitization test."""
    success = await test_schema_sanitization()
    print("\n" + "=" * 60)
    if success:
        print("✓ Schema sanitization test PASSED")
    else:
        print("✗ Schema sanitization test FAILED")
    print("=" * 60)
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
