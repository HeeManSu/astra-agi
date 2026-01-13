"""
Example: Using API Client to Test HTTP Endpoints.

This demonstrates Approach 2: Using the API client to test HTTP endpoints.
Requires the server to be running (main.py).

Run with:
    cd packages/runtime
    uv run --package astra-runtime python examples/team_workflow/example_api_client.py

Or start the server first:
    1. Terminal 1: uv run --package astra-runtime python examples/team_workflow/main.py
    2. Terminal 2: uv run --package astra-runtime python examples/team_workflow/example_api_client.py
"""

import asyncio
from pathlib import Path
import sys


# Add project root to sys.path so we can import 'examples'
# This allows running the script from anywhere using correct imports
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from examples.team_workflow.api_client import TeamAPIClient  # noqa: E402


async def example_list_teams(client: TeamAPIClient):
    """Example 1: List all available teams."""
    print("Example 1: List All Teams")

    try:
        teams = await client.list_teams()
        print(f"\nFound {len(teams)} teams:\n")
        for team in teams:
            print(f"{team['id']}: {team['name']}")
            print(f"Mode: {team['execution_mode']}")
            print(f"Members: {team['member_count']}")
            print(f"Model: {team['model']}")
            print()
    except Exception as e:
        print(f"Error listing teams: {e}")
        return False

    return True


async def example_get_team_details(client: TeamAPIClient):
    """Example 2: Get detailed information about a specific team."""
    print("Example 2: Get Team Details")

    try:
        team_id = "order-processing-team"
        team_details = await client.get_team(team_id)

        print(f"\nTeam: {team_details['name']}")
        print(f"ID: {team_details['id']}")
        print(f"Execution Mode: {team_details['execution_mode']}")
        print(f"\nMembers ({len(team_details['members'])}):")
        for member in team_details["members"]:
            print(f"{member['id']}: {member['name']}")
            print(f"Description: {member['description']}")
        print("\nConfiguration:")
        config = team_details["configuration"]
        print(f"Max Delegations: {config['max_delegations']}")
        print(f"Timeout: {config['timeout']}s")
        print(f"Member Timeout: {config['member_timeout']}s")
        print(f"Allow Parallel: {config['allow_parallel']}")
        print(f"Max Parallel: {config['max_parallel']}")
    except Exception as e:
        print(f"Error getting team details: {e}")
        return False

    return True


async def example_process_order(client: TeamAPIClient):
    """Example 3: Process a complete order using Order Processing Team."""
    print("Example 3: Process Order (Coordinate Mode)")

    order_message = (
        "Process this order: Order ID ORD-001, Customer CUST-100, "
        "Items: [{'product_id': 'PROD-001', 'quantity': 1, 'price': 99.99}], "
        "Shipping: {'country': 'US', 'address': '123 Main St, New York, NY 10001'}, "
        "Payment: {'method': 'credit_card', 'amount': 99.99}"
    )

    try:
        print("\nProcessing order via API...")

        result = await client.generate(
            team_id="order-processing-team",
            message=order_message,
        )

        print("Order processed successfully!")
        print("\nResponse:")
        content = result.get("content", "")
        print(content[:500] + "..." if len(content) > 500 else content)

        if "thread_id" in result:
            print(f"\nThread ID: {result['thread_id']}")

    except Exception as e:
        print(f"Error processing order: {e}")
        return False

    return True


async def example_customer_support(client: TeamAPIClient):
    """Example 4: Handle customer support inquiry (Route Mode)."""
    print("Example 4: Customer Support Inquiry (Route Mode)")

    support_message = "I need help with a refund for order ORD-001"

    try:
        print("\nHandling customer support inquiry...")

        result = await client.generate(
            team_id="customer-support-team",
            message=support_message,
        )

        print("Support inquiry handled!")
        print("\nResponse:")
        content = result.get("content", "")
        print(content[:500] + "..." if len(content) > 500 else content)

    except Exception as e:
        print(f"Error handling support inquiry: {e}")
        return False

    return True


async def example_fraud_detection(client: TeamAPIClient):
    """Example 5: Analyze fraud risk (Collaborate Mode)."""
    print("Example 5: Fraud Detection Analysis (Collaborate Mode)")

    fraud_message = (
        "Analyze fraud risk for order ORD-002: customer CUST-200, "
        "amount $5000, payment_method prepaid_card, "
        "shipping and billing addresses differ"
    )

    try:
        print("\nAnalyzing fraud risk via API...")

        result = await client.generate(
            team_id="fraud-detection-team",
            message=fraud_message,
        )

        print("Fraud analysis completed!")
        print("\nResponse:")
        content = result.get("content", "")
        print(content[:500] + "..." if len(content) > 500 else content)

    except Exception as e:
        print(f"Error analyzing fraud: {e}")
        return False

    return True


async def example_stream_order_processing(client: TeamAPIClient):
    """Example 6: Stream order processing events."""
    print("Example 6: Stream Order Processing (Real-time Events)")

    order_message = (
        "Process this order: Order ID ORD-003, Customer CUST-300, "
        "Items: [{'product_id': 'PROD-002', 'quantity': 2, 'price': 49.99}], "
        "Shipping: {'country': 'US'}, Payment: {'method': 'credit_card', 'amount': 99.98}"
    )

    try:
        print("\nStreaming order processing events...")
        print("Events:")

        event_count = 0
        async for event in client.stream(
            team_id="order-processing-team",
            message=order_message,
        ):
            event_count += 1
            event_type = event.get("event", "unknown")
            data = event.get("data", {})

            print(f"\n[{event_count}] Event: {event_type}")
            if "member_id" in data:
                print(f"Member: {data['member_id']}")
            if "task" in data:
                print(f"Task: {data['task'][:80]}...")
            if "result" in data:
                result_preview = str(data["result"])[:100]
                print(f"Result: {result_preview}...")
            if "chunk" in data:
                print(f"Chunk: {data['chunk'][:100]}...")

        print(f"\nStreamed {event_count} events")

    except Exception as e:
        print(f"Error streaming: {e}")
        return False

    return True


async def example_conversation_with_thread(client: TeamAPIClient):
    """Example 7: Conversation with thread_id for continuity."""
    print("Example 7: Conversation with Thread ID (Memory)")

    thread_id = "api-client-conversation-123"

    try:
        # First message
        print("\nMessage 1: Setting order context...")
        result1 = await client.generate(
            team_id="customer-support-team",
            message="My order number is ORD-001 and I need help",
            thread_id=thread_id,
        )
        print(f"Response 1: {result1.get('content', '')[:200]}...")

        # Second message (should remember context)
        print("\nMessage 2: Asking about the order...")
        result2 = await client.generate(
            team_id="customer-support-team",
            message="What is my order number?",
            thread_id=thread_id,  # Same thread_id for continuity
        )
        print(f"Response 2: {result2.get('content', '')[:200]}...")

        print(f"\nConversation completed with thread_id: {thread_id}")

    except Exception as e:
        print(f"Error in conversation: {e}")
        return False

    return True


async def main():
    """
    Run all API client examples.

    Prerequisites:
        - Server must be running (main.py)
        - Server URL: http://localhost:8000 (default)
    """
    print("E-commerce Order Fulfillment - API Client Examples")
    base_url = "http://localhost:8000"
    client = TeamAPIClient(base_url=base_url)

    try:
        # Test connection
        print(f"Connecting to server at {base_url}...")
        await client.list_teams()
        print("Connected successfully!")

        # Run examples
        examples = [
            # ("List Teams", example_list_teams),
            # ("Get Team Details", example_get_team_details),
            ("Process Order", example_process_order),
            # ("Customer Support", example_customer_support),
            # ("Fraud Detection", example_fraud_detection),
            # ("Stream Order Processing", example_stream_order_processing),
            # ("Conversation with Thread", example_conversation_with_thread),
        ]

        results = []
        for name, example_func in examples:
            success = False
            try:
                success = await example_func(client)
            except Exception as e:
                print(f"Example '{name}' failed: {e}")
            finally:
                results.append((name, success))

        # Summary
        print("Summary")
        for name, success in results:
            status = "PASSED" if success else "FAILED"
            print(f"{status}: {name}")

        passed = sum(1 for _, success in results if success)
        total = len(results)
        print(f"Total: {passed}/{total} examples passed")

    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
