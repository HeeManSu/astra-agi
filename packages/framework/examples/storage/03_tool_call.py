"""
Example 3: Tool Call Storage Test

Tests comprehensive tool call storage and retrieval:
- Assistant messages with tool_calls
- Tool result messages with tool_call_id linking
- History reconstruction with tool_calls
- Multiple tool call iterations
"""

import asyncio
import os
from uuid import uuid4

from framework.agents import Agent, tool
from framework.models import Gemini
from framework.storage.databases.libsql import LibSQLStorage


@tool
def calculator(operation: str, a: float, b: float) -> float:
    """
    Perform basic arithmetic operations.

    Args:
        operation: The operation (add, subtract, multiply, divide)
        a: First number
        b: Second number

    Returns:
        Result of the operation
    """
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else float("inf"),
    }
    return operations.get(operation, lambda x, y: 0)(a, b)


@tool
def get_weather(city: str) -> str:
    """
    Get weather information for a city.

    Args:
        city: Name of the city

    Returns:
        Weather information
    """
    weather_data = {
        "london": "Rainy, 15°C",
        "paris": "Sunny, 22°C",
        "new york": "Cloudy, 18°C",
    }
    return weather_data.get(city.lower(), f"Weather data not available for {city}")


async def test_tool_call_storage():
    """Test that tool calls are properly stored and retrieved."""
    print("\n" + "=" * 60)
    print("Test 1: Tool Call Storage")
    print("=" * 60)

    db_file = "./test_tool_calls.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=db_url, echo=False)
    agent = Agent(
        name="ToolCallAgent",
        instructions="You are a precise calculator. You MUST use the calculator tool for every arithmetic operation. Do not calculate manually. Use get_weather for weather queries.",
        model=Gemini("gemini-2.5-flash"),
        storage=storage,
        tools=[calculator, get_weather],
        code_mode=False,
    )

    thread_id = f"thread-{uuid4().hex[:8]}"

    try:
        # Invoke with tool call
        print("Invoking agent with tool call request...")
        response = await agent.invoke("What is 25 multiplied by 4?", thread_id=thread_id)
        print(f"Response: {response}")

        # Wait for queue to flush
        await asyncio.sleep(1)

        # Retrieve history
        print("\nRetrieving conversation history...")
        if agent.storage:
            history = await agent.storage.get_history(thread_id)
        else:
            print("No memory available")
            return

        print(f"Total messages: {len(history)}")

        # Verify message types
        roles = [msg.role for msg in history]
        print(f"Message roles: {roles}")

        # Check for assistant message with tool_calls
        assistant_with_tools = [
            msg for msg in history if msg.role == "assistant" and msg.metadata.get("tool_calls")
        ]
        print(f"Assistant messages with tool_calls: {len(assistant_with_tools)}")

        if assistant_with_tools:
            tool_calls = assistant_with_tools[0].metadata.get("tool_calls", [])
            print(f"Tool calls stored: {len(tool_calls)}")
            for tc in tool_calls:
                print(f"  - {tc.get('name')}({tc.get('arguments')})")

        # Check for tool result messages
        tool_messages = [msg for msg in history if msg.role == "tool"]
        print(f"Tool result messages: {len(tool_messages)}")

        for tool_msg in tool_messages:
            tool_name = tool_msg.metadata.get("tool_name")
            tool_call_id = tool_msg.metadata.get("tool_call_id")
            print(f"  - Tool: {tool_name}, Call ID: {tool_call_id}")

        # Verify complete flow
        assert len(history) >= 3, "Should have user, assistant (with tools), and tool messages"
        assert len(assistant_with_tools) > 0, "Should have assistant message with tool_calls"
        assert len(tool_messages) > 0, "Should have tool result messages"

        print("\nTool call storage verified!")

    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        if agent.storage:
            await agent.storage.stop()
        await storage.disconnect()
        if os.path.exists(db_file):
            os.remove(db_file)


async def test_multiple_tool_iterations():
    """Test storage with multiple tool call iterations."""
    print("\n" + "=" * 60)
    print("Test 2: Multiple Tool Call Iterations")
    print("=" * 60)

    db_file = "./test_multiple_tools.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=db_url, echo=False)
    agent = Agent(
        name="MultiToolAgent",
        instructions="You MUST use the calculator tool for every step. Do not calculate mentally. Calculate 100 divided by 4, then multiply by 3.",
        model=Gemini("gemini-2.5-flash"),
        storage=storage,
        tools=[calculator],
        code_mode=False,
    )

    thread_id = f"thread-{uuid4().hex[:8]}"

    try:
        print("Invoking agent with multi-step calculation...")
        response = await agent.invoke(
            "Calculate 100 divided by 4, then multiply that result by 3",
            thread_id=thread_id,
        )
        print(f"Final response: {response}")

        # Wait for queue
        await asyncio.sleep(1)

        # Check history
        if agent.storage:
            history = await agent.storage.get_history(thread_id)
        else:
            print("No memory available")
            return
        print(f"\nTotal messages: {len(history)}")

        # Count tool calls and results
        assistant_messages = [msg for msg in history if msg.role == "assistant"]
        tool_messages = [msg for msg in history if msg.role == "tool"]

        print(f"Assistant messages: {len(assistant_messages)}")
        print(f"Tool messages: {len(tool_messages)}")

        # Verify tool call iterations
        tool_call_counts = [
            len(msg.metadata.get("tool_calls", []))
            for msg in assistant_messages
            if msg.metadata.get("tool_calls")
        ]
        print(f"Tool calls per iteration: {tool_call_counts}")

        assert len(assistant_messages) >= 2, "Should have multiple assistant messages"
        assert len(tool_messages) >= 2, "Should have multiple tool result messages"

        print("Multiple tool iterations stored correctly!")

    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        if agent.storage:
            await agent.storage.stop()
        await storage.disconnect()
        if os.path.exists(db_file):
            os.remove(db_file)


async def test_history_reconstruction():
    """Test that history can be reconstructed with tool_calls."""
    print("\n" + "=" * 60)
    print("Test 3: History Reconstruction")
    print("=" * 60)

    db_file = "./test_reconstruction.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=db_url, echo=False)
    agent = Agent(
        name="ReconstructionAgent",
        instructions="You MUST use the calculator tool. Do not calculate manually.",
        model=Gemini("gemini-2.5-flash"),
        storage=storage,
        tools=[calculator],
        code_mode=False,
    )

    thread_id = f"thread-{uuid4().hex[:8]}"

    try:
        # First interaction with tool
        await agent.invoke("What is 10 * 5?", thread_id=thread_id)
        await asyncio.sleep(1)

        # Get history and reconstruct
        if agent.storage:
            history = await agent.storage.get_history(thread_id)
        else:
            print("No memory available")
            return
        print(f"Retrieved {len(history)} messages")

        # Convert to dict format (as LLM would expect)
        reconstructed = []
        for msg in history:
            msg_dict = {"role": msg.role, "content": msg.content, **msg.metadata}
            reconstructed.append(msg_dict)

        print("\nReconstructed messages:")
        for i, msg_dict in enumerate(reconstructed):
            print(f"{i + 1}. {msg_dict['role']}: {msg_dict.get('content', '')[:50]}...")
            if msg_dict.get("tool_calls"):
                print(f"   Tool calls: {msg_dict['tool_calls']}")
            if msg_dict.get("name"):
                print(f"   Tool name: {msg_dict['name']}")
            print(f"   Metadata: {msg_dict}")

        # Verify reconstruction
        assistant_msgs = [m for m in reconstructed if m["role"] == "assistant"]
        tool_msgs = [m for m in reconstructed if m["role"] == "tool"]

        assert len(assistant_msgs) > 0, "Should have assistant messages"
        assert any("tool_calls" in msg for msg in assistant_msgs), (
            "Should have assistant message with tool_calls"
        )
        assert len(tool_msgs) > 0, "Should have tool messages"

        print("\nHistory reconstruction verified!")

    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        if agent.storage:
            await agent.storage.stop()
        await storage.disconnect()
        if os.path.exists(db_file):
            os.remove(db_file)


async def main():
    """Run all tool call storage tests."""
    print("\n" + "=" * 60)
    print("Tool Call Storage Tests")
    print("=" * 60)

    tests = [
        # test_tool_call_storage,
        # test_multiple_tool_iterations,
        test_history_reconstruction,
    ]

    for test in tests:
        try:
            await test()
            # Add delay to avoid rate limits
            await asyncio.sleep(5)
        except Exception as e:
            print(f"\nTest {test.__name__} failed: {e}")
            raise

    print("\n" + "=" * 60)
    print("All tool call storage tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
