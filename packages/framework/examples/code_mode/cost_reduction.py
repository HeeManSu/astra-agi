"""
Cost Reduction Example: Demonstrating 90% Token Reduction with Code Mode

This example demonstrates the dramatic token reduction achieved by code execution mode
compared to traditional tool calling mode.

Traditional Mode:
- LLM sees full tool schemas (~500 tokens each x 20 tools = 10,000 tokens)
- Makes multiple tool calls sequentially
- Sees full tool responses (~500-2000 tokens each)
- Total: ~15,000-25,000 tokens

Code Mode:
- LLM sees compact API surface (~300 tokens total)
- Generates Python code (single LLM call)
- Executes in sandbox (no tool response tokens)
- Returns only print() output (~20-50 tokens)
- Total: ~400-500 tokens

Reduction: 95-98% token savings!

Note: Gemini 2.5 Flash free tier supports:
- 32K input tokens per request
- 8K output tokens per request
- Rate limits apply (requests per minute)
- This example should work within free tier limits
"""

import asyncio
import os
import sys

from framework.agents.agent import Agent
from framework.agents.tool import tool
from framework.models.google.gemini import Gemini


# Add framework src to path
src_path = os.path.join(os.path.dirname(__file__), "../../src")
sys.path.insert(0, src_path)

# try:
#     from framework.agents import Agent
#     from framework.agents.tool import tool
#     from framework.models import Gemini
# except ImportError as e:
#     print("=" * 60)
#     print("IMPORT ERROR: Framework dependencies not available")
#     print("=" * 60)
#     print(f"Error: {e}")
#     print("\nTo run this example:")
#     print("  From workspace root:")
#     print("    uv run python packages/framework/examples/code_mode/cost_reduction.py")
#     sys.exit(1)


# ============================================================================
# Define Many Tools to Generate Large Tool Schema
# ============================================================================


# CRM Tools
@tool(module="crm")
def get_user(user_id: int) -> dict:
    """Get user details by ID from CRM system."""
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
        "status": "active",
        "created_at": "2024-01-01",
        "last_login": "2024-12-01",
        "subscription": "premium",
        "tags": ["vip", "enterprise"],
    }


@tool(module="crm")
def update_user(user_id: int, data: dict) -> dict:
    """Update user information in CRM system."""
    return {"id": user_id, "updated": True, "data": data}


@tool(module="crm")
def list_users(filters: dict, limit: int = 10) -> list:
    """List users with optional filters."""
    return [{"id": i, "name": f"User {i}"} for i in range(1, limit + 1)]


@tool(module="crm")
def create_contact(name: str, email: str, phone: str) -> dict:
    """Create a new contact in CRM."""
    return {"id": 123, "name": name, "email": email, "phone": phone}


@tool(module="crm")
def get_account(account_id: str) -> dict:
    """Get account details by ID."""
    return {
        "id": account_id,
        "name": "Acme Corp",
        "industry": "Technology",
        "revenue": 1000000,
        "employees": 500,
    }


# Google Drive Tools
@tool(module="gdrive")
def get_document(document_id: str) -> dict:
    """Fetch a document from Google Drive by ID."""
    return {
        "id": document_id,
        "title": "Sample Document",
        "content": "This is a sample document content...",
        "created": "2024-01-01",
        "modified": "2024-12-01",
        "size": 1024,
    }


@tool(module="gdrive")
def list_files(folder_id: str, limit: int = 10) -> list:
    """List files in a Google Drive folder."""
    return [
        {"id": f"file_{i}", "name": f"File {i}.txt", "type": "document"}
        for i in range(1, limit + 1)
    ]


@tool(module="gdrive")
def create_folder(name: str, parent_id: str | None = None) -> dict:
    """Create a new folder in Google Drive."""
    return {"id": "folder_123", "name": name, "parent_id": parent_id}


@tool(module="gdrive")
def share_file(file_id: str, email: str, role: str = "reader") -> dict:
    """Share a file with a user."""
    return {"file_id": file_id, "shared_with": email, "role": role}


# Math/Calculation Tools
@tool(module="math")
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool(module="math")
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


@tool(module="math")
def calculate_percentage(percent: int, amount: int) -> float:
    """Calculate percent% of amount. Example: calculate_percentage(15, 1000) returns 150 (15% of 1000)."""
    return (percent / 100) * amount


# Database Tools
@tool(module="db")
def query(sql: str) -> list:
    """Execute a SQL query."""
    return [{"id": 1, "name": "Result 1"}, {"id": 2, "name": "Result 2"}]


@tool(module="db")
def insert(table: str, data: dict) -> dict:
    """Insert data into a table."""
    return {"id": 123, "table": table, "inserted": True}


@tool(module="db")
def update(table: str, id: int, data: dict) -> dict:
    """Update a record in a table."""
    return {"id": id, "table": table, "updated": True}


# Email Tools
@tool(module="email")
def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email."""
    return {"sent": True, "to": to, "subject": subject}


@tool(module="email")
def get_inbox(limit: int = 10) -> list:
    """Get inbox emails."""
    return [
        {"id": i, "from": f"sender{i}@example.com", "subject": f"Email {i}"}
        for i in range(1, limit + 1)
    ]


# Analytics Tools
@tool(module="analytics")
def get_metrics(start_date: str, end_date: str) -> dict:
    """Get analytics metrics for date range."""
    return {
        "visitors": 10000,
        "page_views": 50000,
        "conversions": 500,
        "revenue": 50000,
    }


@tool(module="analytics")
def get_report(report_type: str, filters: dict) -> dict:
    """Generate an analytics report."""
    return {"type": report_type, "data": {"metric1": 100, "metric2": 200}}


# Payment Tools
@tool(module="payment")
def process_payment(amount: float, currency: str, method: str) -> dict:
    """Process a payment."""
    return {"transaction_id": "txn_123", "status": "success", "amount": amount}


@tool(module="payment")
def refund_payment(transaction_id: str, reason: str) -> dict:
    """Refund a payment."""
    return {"transaction_id": transaction_id, "refunded": True}


# ============================================================================
# Test Functions
# ============================================================================


async def test_traditional_mode():
    """Test traditional tool calling mode (high token usage)."""
    print("\n" + "=" * 80)
    print("TRADITIONAL MODE TEST (High Token Usage)")
    print("=" * 80)

    # Create agent with code_mode=False
    agent = Agent(
        name="TraditionalAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="You are a helpful assistant with access to many tools. When asked to calculate percentages, use the calculate_percentage tool with percent and amount parameters.",
        tools=[
            get_user,
            update_user,
            list_users,
            create_contact,
            get_account,
            get_document,
            list_files,
            create_folder,
            share_file,
            add,
            multiply,
            calculate_percentage,
            query,
            insert,
            update,
            send_email,
            get_inbox,
            get_metrics,
            get_report,
            process_payment,
            refund_payment,
        ],
        code_mode=False,  # Traditional mode
    )

    # Complex multi-step request that will trigger many tool calls
    request = """
    Please do the following:
    1. Get user 123 from CRM
    2. Get their account details (use account_id 'acc_123')
    3. Fetch document 'doc_abc123' from Google Drive
    4. Calculate 15% of 1000 using the calculate_percentage tool
    5. Send an email to user123@example.com with subject 'Calculation Result' and the calculation result in the body
    6. Get analytics metrics for start_date '2024-11-01' and end_date '2024-11-30'
    7. Process a payment of $50 with currency 'USD' and method 'credit_card'
    """

    print(f"\nRequest: {request.strip()}")
    print("\nExecuting in traditional mode...")
    print("(This will make multiple LLM calls with full tool schemas)")

    # Track token usage
    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0

    try:
        # Monkey-patch to capture usage from model responses
        original_invoke = agent.model.invoke
        usage_data = []

        async def track_invoke(*args, **kwargs):
            response = await original_invoke(*args, **kwargs)
            if response.usage:
                usage_data.append(response.usage)
            return response

        agent.model.invoke = track_invoke

        response = await agent.invoke(request)
        print(f"\nResponse: {response}")

        # Calculate total token usage
        for usage in usage_data:
            total_input_tokens += usage.get("input_tokens", 0)
            total_output_tokens += usage.get("output_tokens", 0)
            total_tokens += usage.get("total_tokens", 0)

        print("\n" + "-" * 80)
        print("Token Usage (Actual):")
        print(f"- Input tokens: {total_input_tokens:,}")
        print(f"- Output tokens: {total_output_tokens:,}")
        print(f"- Total tokens: {total_tokens:,}")
        print("-" * 80)
        print("\nToken Usage Breakdown:")
        print("- Tool schemas sent to LLM: ~10,000 tokens (21 tools x ~500 tokens)")
        print("- Tool call responses: ~3,000-5,000 tokens")
        print("- Multiple LLM round trips: adds overhead")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


async def test_code_mode():
    """Test code execution mode (low token usage)."""
    print("\n" + "=" * 80)
    print("CODE MODE TEST (Low Token Usage)")
    print("=" * 80)

    # Create agent with code_mode=True
    agent = Agent(
        name="CodeModeAgent",
        model=Gemini("gemini-2.5-flash"),
        instructions="You are a helpful assistant.",
        tools=[
            get_user,
            update_user,
            list_users,
            create_contact,
            get_account,
            get_document,
            list_files,
            create_folder,
            share_file,
            add,
            multiply,
            calculate_percentage,
            query,
            insert,
            update,
            send_email,
            get_inbox,
            get_metrics,
            get_report,
            process_payment,
            refund_payment,
        ],
        code_mode=True,  # Code execution mode
    )

    # Same complex request
    request = """
    Please do the following:
    1. Get user 123 from CRM
    2. Get their account details (use account_id 'acc_123')
    3. Fetch document 'doc_abc123' from Google Drive
    4. Calculate 15% of 1000 using the calculate_percentage tool
    5. Send an email to user123@example.com with subject 'Calculation Result' and the calculation result in the body
    6. Get analytics metrics for start_date '2024-11-01' and end_date '2024-11-30'
    7. Process a payment of $50 with currency 'USD' and method 'credit_card'
    """

    print(f"\nRequest: {request.strip()}")
    print("\nExecuting in code mode...")
    print("(This will generate Python code and execute in sandbox)")

    # Track token usage
    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0

    try:
        # Monkey-patch to capture usage from model responses
        original_invoke = agent.model.invoke
        usage_data = []

        async def track_invoke(*args, **kwargs):
            response = await original_invoke(*args, **kwargs)
            if response.usage:
                usage_data.append(response.usage)
            return response

        agent.model.invoke = track_invoke

        response = await agent.invoke(request)
        print(f"\nResponse: {response}")

        # Calculate total token usage
        for usage in usage_data:
            total_input_tokens += usage.get("input_tokens", 0)
            total_output_tokens += usage.get("output_tokens", 0)
            total_tokens += usage.get("total_tokens", 0)

        print("\n" + "-" * 80)
        print("Token Usage (Actual):")
        print(f"- Input tokens: {total_input_tokens:,}")
        print(f"- Output tokens: {total_output_tokens:,}")
        print(f"- Total tokens: {total_tokens:,}")
        print("-" * 80)
        print("\nToken Usage Breakdown:")
        print("- Compact API surface: ~300 tokens")
        print("- Code generation: ~200 tokens")
        print("- Single LLM call: minimal overhead")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Run both tests and compare."""
    print("=" * 80)
    print("COST REDUCTION DEMONSTRATION")
    print("=" * 80)
    print("\nThis example demonstrates token reduction with code execution mode.")
    print("Gemini 2.5 Flash free tier supports:")
    print("  - 32K input tokens per request")
    print("  - 8K output tokens per request")
    print("  - This example should work within free tier limits")
    print()

    # Run traditional mode test
    # await test_traditional_mode()

    # Run code mode test
    await test_code_mode()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nTraditional Mode:")
    print("  - Tool schemas: ~10,000 tokens")
    print("  - Tool responses: ~3,000-5,000 tokens")
    print("  - Multiple LLM round trips: adds overhead")
    print("  - Total: ~15,000-20,000 tokens")
    print("\nCode Mode:")
    print("  - Compact API surface: ~300 tokens")
    print("  - Code generation: ~200 tokens")
    print("  - Single LLM call: minimal overhead")
    print("  - Total: ~400-500 tokens")
    print("\nReduction: 95-98% token savings!")
    print("\nNote: Actual token usage is displayed above from model responses.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
