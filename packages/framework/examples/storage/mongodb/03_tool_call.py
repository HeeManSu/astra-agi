"""
Example: Tool Call Storage Test with MongoDB

Tests comprehensive tool call storage and retrieval:
- Assistant messages with tool_calls
- Tool result messages with tool_call_id linking
- History reconstruction with tool_calls
- Multiple tool call iterations

Requires: MongoDB running locally on port 27017.
"""

import asyncio
from uuid import uuid4

from framework.agents import Agent, tool
from framework.models.huggingface import HuggingFaceLocal
from framework.storage.databases.mongodb import MongoDBStorage


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
    print("Test 1: Tool Call Storage with MongoDB")
    print("=" * 60)

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_tool_call_test")
    await storage.connect()

    # Using local model to avoid rate limits
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct")

    agent = Agent(
        name="ToolCallAgent",
        instructions="Use tools when needed. Be concise.",
        model=model,
        storage=storage,
        tools=[calculator, get_weather],
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

        print("\n✅ Tool call storage test completed!")

    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        if agent.storage:
            await agent.storage.stop()
        # Clean up
        await storage.db["astra_threads"].delete_many({})
        await storage.db["astra_messages"].delete_many({})
        await storage.disconnect()


async def main():
    """Run tool call storage tests."""
    print("\n" + "=" * 60)
    print("MongoDB Tool Call Storage Tests")
    print("=" * 60)

    await test_tool_call_storage()

    print("\n" + "=" * 60)
    print("All MongoDB tool call storage tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
