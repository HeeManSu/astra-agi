"""
Example 11: Comprehensive API Surface Generation

Demonstrates ALL possible tool registration methods:
1. Python tools with explicit module parameter
2. Python tools with dot notation in name
3. Python tools without module (default)
4. Python tools with dot notation AND explicit module override
5. MCP servers directly from MCPRegistry
6. Custom MCPServer instances (stdio transport)
7. Custom MCPServer instances (HTTP transport)
8. Custom MCPServer instances (with env variables)
9. MCPManager with preset name servers
10. MCPManager with MCPServer instances

Then generates and displays the compact API surface.
"""

import asyncio
import os
from pathlib import Path
import sys

from framework.agents import Agent
from framework.agents.tool import tool
from framework.mcp import MCPManager, MCPRegistry, MCPServer
from framework.models import Gemini


# Add src to path
src_path = os.path.join(os.path.dirname(__file__), "../../src")
sys.path.insert(0, src_path)


print("=" * 80)
print("COMPREHENSIVE API SURFACE GENERATION EXAMPLE")
print("=" * 80)
print()

# ============================================================================
# 1. Python Tools with Explicit Module Parameter
# ============================================================================
print("Step 1: Define Python Tools with Explicit Module Parameter")


@tool(module="math")
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool(module="math")
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


@tool(module="crm")
def get_user(user_id: int) -> dict:
    """Get a user by ID from CRM."""
    return {"id": user_id, "name": "John Doe"}


@tool(module="crm")
def update_user(user_id: int, data: dict) -> dict:
    """Update user information in CRM."""
    return {"id": user_id, "updated": True}


@tool(module="utils")
def format_text(text: str, uppercase: bool = False) -> str:
    """Format text with optional uppercase conversion."""
    return text.upper() if uppercase else text


print("   ✓ Created 5 Python tools with explicit modules (math, crm, utils)")
print()

# ============================================================================
# 2. Python Tools with Dot Notation in Name
# ============================================================================
print("Step 2: Define Python Tools with Dot Notation in Name")


@tool(name="gdrive.get_document")
def get_document(document_id: str) -> dict:
    """Fetch a document content by ID."""
    return {"id": document_id, "content": "..."}


@tool(name="gdrive.list_files")
def list_files(folder_id: str) -> list:
    """List files within a folder."""
    return []


print("   ✓ Created 2 Python tools with dot notation (gdrive)")
print()

# ============================================================================
# 3. Python Tools without Module (Default)
# ============================================================================
print("Step 3: Define Python Tools without Explicit Module")


@tool
def helper_function(x: str) -> str:
    """A helper function without explicit module."""
    return x.upper()


print("   ✓ Created 1 Python tool without module (will use 'default')")
print()

# ============================================================================
# 4. Python Tools with Dot Notation AND Explicit Module Override
# ============================================================================
print("Step 4: Define Python Tools with Dot Notation AND Explicit Module")


@tool(name="salesforce.get_account", module="crm")
def get_account(account_id: str) -> dict:
    """Get account from Salesforce (but in CRM module)."""
    return {"id": account_id, "name": "Acme Corp"}


@tool(name="jira.create_ticket")
def create_ticket(title: str, description: str) -> dict:
    """Create a Jira issue with title and description."""
    return {"id": "TICKET-123", "title": title}


@tool(name="jira.update_ticket", module="jira")
def update_ticket(issue_id: str, fields: dict) -> dict:
    """Update fields of an existing Jira issue."""
    return {"id": issue_id, "updated": True}


print("   ✓ Created 3 Python tools:")
print("     - 1 with dot notation + explicit module override (crm)")
print("     - 2 with dot notation (jira)")
print()

# ============================================================================
# 5. MCP Servers from MCPRegistry (Direct)
# ============================================================================
print("Step 5: Create MCP Servers Directly from MCPRegistry")

# Method 5a: Direct from registry static methods
fs_server = MCPRegistry.filesystem(path=".")
print("   ✓ Created filesystem MCP server (direct from registry)")

memory_server = MCPRegistry.memory()
print("   ✓ Created memory MCP server (direct from registry)")

# Note: sqlite server removed as it doesn't exist in npm registry
# sqlite_server = MCPRegistry.sqlite(path=":memory:")

print()

# ============================================================================
# 6. Custom MCPServer Instance (Not from Registry)
# ============================================================================
print("Step 6: Create Custom MCPServer Instances")

# Method 6a: Custom server with command (stdio transport)
# Using a real MCP server package for demonstration
custom_server = MCPServer(
    name="custom_calculator",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-calculator"],
)
print("   ✓ Created custom MCPServer instance (stdio transport with command)")

# Method 6b: Custom server with URL (HTTP transport)
# Note: This is a mock example - in real usage you'd have a valid URL
# For demonstration, we'll create it but it won't connect
http_server = MCPServer(
    name="http_api",
    url="http://localhost:8000/mcp",  # Mock URL for example
)
print("   ✓ Created custom MCPServer instance (HTTP transport with URL)")

# Method 6c: Custom server with environment variables
# Using a real MCP server with env vars
env_server = MCPServer(
    name="env_weather",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-weather"],
    env={"OPENWEATHERMAP_API_KEY": "test_key"},
)
print("   ✓ Created custom MCPServer instance (with env variables)")

print()

# ============================================================================
# 7. MCPManager with Multiple Servers
# ============================================================================
print("Step 7: Create MCPManager and Add Servers")

mcp_manager = MCPManager()

# Method 7a: Add server using preset name (string)
# Method 7b: Add server using MCPServer instance
# Note: We'll add these in the async function since add_server is async
print("   ✓ Created MCPManager")
print("   ℹ  Will add servers to manager in async function")
print()

# ============================================================================
# 8. Create Agent with All Tools
# ============================================================================
print("=" * 80)
print("Step 8: Create Agent with All Tools")
print("=" * 80)

all_tools = [
    # Python tools with explicit modules
    add,
    multiply,
    get_user,
    update_user,
    format_text,
    # Python tools with dot notation
    get_document,
    list_files,
    # Python tools without module
    helper_function,
    # Python tools with dot notation + explicit module
    get_account,
    create_ticket,
    update_ticket,
    # MCP servers directly from registry
    fs_server,
    memory_server,
    # Custom MCP servers
    custom_server,
    http_server,
    env_server,
    # MCPManager (will add more servers to it)
    mcp_manager,
]

print(f"   Total tools to register: {len(all_tools)}")
print("   - 5 Python tools (explicit modules)")
print("   - 2 Python tools (dot notation)")
print("   - 1 Python tool (default module)")
print("   - 3 Python tools (dot notation + explicit module)")
print("   - 2 MCP servers (direct from registry)")
print("   - 3 Custom MCP servers")
print("   - 1 MCPManager (will add 3 more servers)")
print()

agent = Agent(
    name="ComprehensiveAgent",
    model=Gemini("gemini-2.5-flash"),
    instructions="You are a comprehensive assistant with access to multiple tools.",
    tools=all_tools,
    code_mode=True,
)

print("   ✓ Agent created with code_mode=True")
print()

# ============================================================================
# 9. Invoke Agent to Trigger Tool Registry Population
# ============================================================================
print("=" * 80)
print("Step 9: Invoke Agent to Populate Tool Registry")
print("=" * 80)


async def main():
    try:
        # ============================================================================
        # Add servers to MCPManager (async operation)
        # ============================================================================
        print("=" * 80)
        print("Step 9a: Add Servers to MCPManager")
        print("=" * 80)

        # Method 7a: Add server using preset name (string)
        await mcp_manager.add_server("weather", {"api_key": "test_key"})
        print("   ✓ Added weather server (using preset name string)")

        # Method 7b: Add server using MCPServer instance
        calculator_server = MCPRegistry.calculator()
        await mcp_manager.add_server(calculator_server)
        print("   ✓ Added calculator server (using MCPServer instance)")

        # Method 7c: Add another server using preset name
        await mcp_manager.add_server("github", {"token": "test_token"})
        print("   ✓ Added github server (using preset name string)")

        print(f"   Total servers in manager: {len(mcp_manager.servers)}")
        print()

        # Invoke agent (this triggers lazy initialization of tool registry)
        # Note: Some MCP servers may fail to connect, but Python tools will still work
        print("=" * 80)
        print("Step 9b: Invoke Agent to Populate Tool Registry")
        print("=" * 80)
        print("   Invoking agent (this may take a moment)...")
        print("   Note: MCP connection errors are expected if servers aren't configured")
        print("         Python tools will still be registered and shown in API surface")
        print()

        try:
            await agent.invoke("Hello")
            print("   ✓ Agent invoked successfully")
        except Exception as mcp_error:
            # MCP errors are expected - continue to show Python tools
            error_type = type(mcp_error).__name__
            print(f"   ✘  MCP connection error (expected): {error_type}")
            print("   ✓ Continuing to show Python tools and API surface")
            print("   ℹ  Python tools are registered even if MCP servers fail")
        print()

        # ============================================================================
        # 10. Display Tool Registry Statistics
        # ============================================================================
        print("=" * 80)
        print("Step 10: Display Tool Registry Statistics")
        print("=" * 80)
        print()
        print("Registration Methods Demonstrated:")
        print("  ✔ Python tools with explicit module parameter")
        print("  ✔ Python tools with dot notation in name")
        print("  ✔ Python tools without module (default)")
        print("  ✔ Python tools with dot notation + explicit module override")
        print("  ✔ MCP servers directly from MCPRegistry")
        print("  ✔ Custom MCPServer instances (stdio transport)")
        print("  ✔ Custom MCPServer instances (HTTP transport)")
        print("  ✔ Custom MCPServer instances (with env variables)")
        print("  ✔ MCPManager with preset name servers (string)")
        print("  ✔ MCPManager with MCPServer instances")
        print()
        print("Note: MCP servers may fail to connect if not configured.")
        print("      Python tools will always work and be shown in API surface.")
        print()

        total_tools = len(agent.tool_registry)
        python_tools = agent.tool_registry.get_python_tools()
        mcp_tools = agent.tool_registry.get_mcp_tools()

        print(f"   Total tools registered: {total_tools}")
        print(f"   Python tools: {len(python_tools)}")
        print(f"   MCP tools: {len(mcp_tools)}")
        print()

        # Group by module
        grouped = agent.tool_registry.get_specs_grouped_by_module()
        print("   Tools grouped by module:")
        for module, tools in sorted(grouped.items()):
            print(f"     - {module}: {len(tools)} tools")
            for tool_spec in sorted(tools, key=lambda t: t.name):
                tool_type = "MCP" if tool_spec.is_mcp else "Python"
                print(f"       - {tool_spec.name} ({tool_type})")
        print()

        # ============================================================================
        # 11. Generate and Display Compact API Surface
        # ============================================================================
        print("=" * 80)
        print("Step 11: Generate and Display Compact API Surface")
        print("=" * 80)
        print()
        print("This is the format that will be sent to LLM prompts:")
        print()
        print("-" * 80)
        api_surface = agent.api_surface
        print(api_surface)
        print("-" * 80)
        print()

        # ============================================================================
        # 12. Generate Python API File
        # ============================================================================
        print("=" * 80)
        print("Step 12: Generate Python API File")
        print("=" * 80)
        print()
        api_file_path = agent.api_generator.generate_api_file(agent.tool_registry)
        print(f"✔ Generated API file: {api_file_path}")
        print()
        print("File preview (first 500 characters):")
        print("-" * 80)
        # Read file synchronously (small file, acceptable for example)
        file_content = Path(api_file_path).read_text(encoding="utf-8")
        print(file_content[:500])
        if len(file_content) > 500:
            print("...")
        print("-" * 80)
        print()

        # ============================================================================
        # 13. Summary
        # ============================================================================
        print("=" * 80)
        print("Summary")
        print("=" * 80)
        print(f"✔ Successfully registered {total_tools} tools")
        print(f"✔ Generated compact API surface ({len(api_surface)} characters)")
        print(f"✔ Generated Python API file: {api_file_path}")
        print(f"✔ Tools organized into {len(grouped)} modules")
        print()
        print("All registration methods demonstrated:")
        print("  - 11 Python tools (various registration methods)")
        print("  - Multiple MCP servers (direct and via manager)")
        print("  - Custom MCPServer instances (all transport types)")
        print()
        print("The API surface is ready to be included in LLM prompts for")
        print("code execution mode!")
        print("The API file is ready for sandbox execution!")
        print()

    except Exception as e:
        print()
        print("=" * 80)
        print("Error")
        print("=" * 80)
        print(f"Error occurred: {e}")
        print()
        print("Note: If this is an MCP connection error, that's expected")
        print("in environments without MCP servers configured.")
        print("The tool registry and API surface generation should still work")
        print("for Python tools.")
        print()
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print()
    asyncio.run(main())
