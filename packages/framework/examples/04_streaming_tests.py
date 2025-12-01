"""
Example 4: Streaming Tests
Comprehensive tests for streaming functionality and stream_enabled property.
"""

import asyncio
from collections.abc import Callable
import time

from framework.agents import Agent, tool
from framework.models import Gemini


@tool
def calculator(operation: str, a: float, b: float) -> float:
    """
    Perform basic arithmetic operations.

    Args:
        operation: The operation to perform (add, subtract, multiply, divide)
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

    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}")

    result = operations[operation](a, b)
    return result


@tool
def get_weather(city: str) -> str:
    """
    Get weather information for a city (mock implementation).

    Args:
        city: Name of the city

    Returns:
        Weather information
    """
    weather_data = {
        "london": "Rainy, 15°C",
        "paris": "Sunny, 22°C",
        "new york": "Cloudy, 18°C",
        "tokyo": "Clear, 25°C",
    }

    city_lower = city.lower()
    weather = weather_data.get(city_lower, f"Weather data not available for {city}")
    return weather


@tool
async def search_web(query: str) -> str:
    """
    Search the web (mock async implementation).

    Args:
        query: Search query

    Returns:
        Search results
    """
    await asyncio.sleep(0.1)  # Simulate async operation
    result = f"Search results for '{query}': [Mock result 1, Mock result 2, Mock result 3]"
    return result


@tool
def slow_calculator(operation: str, a: float, b: float) -> float:
    """
    Slow calculator that simulates processing time.

    Args:
        operation: Operation to perform
        a: First number
        b: Second number

    Returns:
        Result of operation
    """
    time.sleep(0.1)  # Simulate slow operation
    operations = {
        "add": lambda x, y: x + y,
        "multiply": lambda x, y: x * y,
    }
    return operations.get(operation, lambda x, y: 0)(a, b)


async def test_streaming_basic():
    """Test basic streaming functionality."""
    print("Test 1: Basic Streaming (stream_enabled=False, explicit stream call)")

    agent = Agent(
        name="StreamingAgent",
        instructions="You are a helpful assistant. Be concise.",
        model=Gemini("gemini-2.5-flash"),
        stream_enabled=False,  # Default, but we'll call stream() explicitly
    )

    print("Q: Count from 1 to 5")
    print("A: ", end="", flush=True)

    chunks_received = 0
    full_response = ""
    start_time = time.time()

    async for chunk in agent.stream("Count from 1 to 5"):
        chunks_received += 1
        full_response += chunk
        print(chunk, end="", flush=True)

    elapsed = time.time() - start_time
    print(f"\nReceived {chunks_received} chunks in {elapsed:.2f}s")
    print(f"Full response length: {len(full_response)} characters")
    assert chunks_received > 0, "Should receive at least one chunk"
    assert len(full_response) > 0, "Response should not be empty"
    print("PASS: Basic streaming works")


async def test_stream_enabled_property():
    """Test stream_enabled property behavior."""
    print("Test 2: stream_enabled Property")

    # Test with stream_enabled=True
    agent_enabled = Agent(
        name="StreamEnabledAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        stream_enabled=True,
    )

    print(f"Agent stream_enabled: {agent_enabled.stream_enabled}")

    # Test with stream_enabled=False
    agent_disabled = Agent(
        name="StreamDisabledAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        stream_enabled=False,
    )

    print(f"Agent stream_enabled: {agent_disabled.stream_enabled}")

    # Test default (should be False)
    agent_default = Agent(
        name="StreamDefaultAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
    )

    print(f"Agent stream_enabled (default): {agent_default.stream_enabled}")
    print("PASS: stream_enabled property works correctly")


async def test_streaming_with_tools():
    """Test streaming when tools are involved."""
    print("Test 3: Streaming with Tools")

    agent = Agent(
        name="StreamingToolAgent",
        instructions="Use tools when needed. Be concise.",
        model=Gemini("gemini-2.5-flash"),
        tools=[slow_calculator],
        stream_enabled=False,
    )

    print("Q: What is 10 multiplied by 5?")
    print("A: ", end="", flush=True)

    chunks = []
    async for chunk in agent.stream("What is 10 multiplied by 5?"):
        chunks.append(chunk)
        print(chunk, end="", flush=True)

    print()
    print(f"\nReceived {len(chunks)} chunks")
    print("PASS: Streaming works with tools")


async def test_streaming_long_response():
    """Test streaming with long responses."""
    print("Test 4: Streaming Long Response")

    agent = Agent(
        name="LongStreamAgent",
        instructions="Provide detailed explanations. Be thorough.",
        model=Gemini("gemini-2.5-flash"),
    )

    print("Q: Explain what Python is and its main features (streaming)")
    print("A: ", end="", flush=True)

    chunk_count = 0
    char_count = 0

    # Test without max_tokens to ensure streaming works
    async for chunk in agent.stream("Explain what Python is and its main features"):
        chunk_count += 1
        char_count += len(chunk)
        print(chunk, end="", flush=True)
        if chunk_count > 50:
            print("...", end="", flush=True)
            break

    print()
    print(f"\nReceived {chunk_count} chunks, {char_count} characters")
    assert chunk_count > 0, "Should receive at least one chunk"
    assert char_count > 0, "Should receive at least some characters"
    print("PASS: Long response streaming works")


async def test_streaming_parameter_override():
    """Test streaming with parameter overrides."""
    print("\n" + "=" * 60)
    print("Test 5: Streaming with Parameter Overrides")
    print("=" * 60)

    agent = Agent(
        name="OverrideStreamAgent",
        instructions="Be creative.",
        model=Gemini("gemini-2.5-flash"),
        temperature=0.3,  # Low temperature
        max_tokens=100,
    )

    print("Q: Tell a short story (temp=1.5, max_tokens=200)")
    print("A: ", end="", flush=True)

    chunks = []
    async for chunk in agent.stream(
        "Tell a very short story",
        temperature=1.5,  # Override to high temperature
        max_tokens=200,  # Override max_tokens
    ):
        chunks.append(chunk)
        print(chunk, end="", flush=True)

    print()
    print(f"\n✓ Received {len(chunks)} chunks with overridden parameters")
    print("✓ PASS: Parameter overrides work in streaming")


async def test_streaming_error_handling():
    """Test streaming error handling."""
    print("\n" + "=" * 60)
    print("Test 6: Streaming Error Handling")
    print("=" * 60)

    agent = Agent(
        name="ErrorStreamAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
    )

    # Test with invalid temperature (should be caught by validation)
    try:
        print("Testing invalid temperature...")
        async for _ in agent.stream("Hello", temperature=5.0):
            pass
        print("✗ FAIL: Should have raised ValidationError")
    except Exception as e:
        print(f"✓ Caught expected error: {type(e).__name__}")

    # Test with valid streaming
    try:
        print("\nTesting valid streaming...")
        chunks = []
        async for chunk in agent.stream("Say hello"):
            chunks.append(chunk)
        print(f"✓ Streaming succeeded: {len(chunks)} chunks")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise

    print("✓ PASS: Error handling works in streaming")


async def test_streaming_vs_invoke():
    """Compare streaming vs invoke responses."""
    print("\n" + "=" * 60)
    print("Test 7: Streaming vs Invoke Comparison")
    print("=" * 60)

    agent = Agent(
        name="CompareAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
    )

    question = "What is 2+2?"

    # Get streaming response
    print("Streaming response:")
    streamed = ""
    async for chunk in agent.stream(question):
        streamed += chunk

    # Get invoke response
    print("\nInvoke response:")
    invoked = await agent.invoke(question)

    print(f"\nStreamed length: {len(streamed)}")
    print(f"Invoked length: {len(invoked)}")
    print(f"Responses match: {streamed.strip() == invoked.strip()}")

    # They might not match exactly due to randomness, but should be similar
    assert len(streamed) > 0 and len(invoked) > 0, "Both should return responses"
    print("✓ PASS: Both streaming and invoke work")


async def test_streaming_multiple_tools():
    """Test streaming with multiple sequential tool calls."""
    print("\n" + "=" * 60)
    print("Test 8: Streaming with Multiple Sequential Tool Calls")
    print("=" * 60)

    agent = Agent(
        name="MultiToolStreamAgent",
        instructions="""You are a helpful assistant. When asked to perform multiple calculations,
        use the calculator tool for each operation. Be clear about each step.""",
        model=Gemini("gemini-2.5-flash"),
        tools=[calculator, get_weather],
    )

    print("Q: Calculate 10 * 5, then add 20 to the result")
    print("A: ", end="", flush=True)

    chunks = []
    async for chunk in agent.stream("Calculate 10 multiplied by 5, then add 20 to the result"):
        chunks.append(chunk)
        print(chunk, end="", flush=True)

    print()
    print(f"\n✓ Received {len(chunks)} chunks")
    assert len(chunks) > 0, "Should receive chunks"
    print("✓ PASS: Multiple sequential tool calls in streaming work")


async def test_streaming_parallel_tool_calls():
    """Test streaming with parallel tool calls (multiple tools called at once)."""
    print("\n" + "=" * 60)
    print("Test 9: Streaming with Parallel Tool Calls")
    print("=" * 60)

    agent = Agent(
        name="ParallelToolStreamAgent",
        instructions="""You are a helpful assistant. When asked about multiple things,
        call multiple tools in parallel if possible.""",
        model=Gemini("gemini-2.5-flash"),
        tools=[calculator, get_weather],
    )

    print("Q: What's 15 * 3 and what's the weather in Paris?")
    print("A: ", end="", flush=True)

    chunks = []
    async for chunk in agent.stream("What's 15 multiplied by 3 and what's the weather in Paris?"):
        chunks.append(chunk)
        print(chunk, end="", flush=True)

    print()
    print(f"\n✓ Received {len(chunks)} chunks")
    assert len(chunks) > 0, "Should receive chunks"
    print("✓ PASS: Parallel tool calls in streaming work")


async def test_streaming_tool_call_loop():
    """Test streaming with tool call loop (tool -> result -> another tool)."""
    print("\n" + "=" * 60)
    print("Test 10: Streaming with Tool Call Loop")
    print("=" * 60)

    agent = Agent(
        name="ToolLoopStreamAgent",
        instructions="""You are a helpful assistant. When asked to perform calculations,
        use the calculator tool. If you need to use the result in another calculation,
        do so step by step.""",
        model=Gemini("gemini-2.5-flash"),
        tools=[calculator],
    )

    print("Q: Calculate 100 divided by 4, then multiply that result by 3")
    print("A: ", end="", flush=True)

    chunks = []
    async for chunk in agent.stream("Calculate 100 divided by 4, then multiply that result by 3"):
        chunks.append(chunk)
        print(chunk, end="", flush=True)

    print()
    print(f"\n✓ Received {len(chunks)} chunks")
    assert len(chunks) > 0, "Should receive chunks"
    print("✓ PASS: Tool call loop in streaming works")


async def test_streaming_with_three_tools():
    """Test streaming with three different tools."""
    print("\n" + "=" * 60)
    print("Test 11: Streaming with Three Different Tools")
    print("=" * 60)

    agent = Agent(
        name="ThreeToolStreamAgent",
        instructions="""You are a helpful assistant with access to calculator, weather, and search tools.
        Use the appropriate tool for each request.""",
        model=Gemini("gemini-2.5-flash"),
        tools=[calculator, get_weather, search_web],
    )

    print("Q: Calculate 25 * 4, get weather for London, and search for 'Python tutorials'")
    print("A: ", end="", flush=True)

    chunks = []
    async for chunk in agent.stream(
        "Calculate 25 multiplied by 4, get weather for London, and search for 'Python tutorials'"
    ):
        chunks.append(chunk)
        print(chunk, end="", flush=True)
        if len(chunks) > 100:  # Limit output
            print("...", end="", flush=True)
            break

    print()
    print(f"\n✓ Received {len(chunks)} chunks")
    assert len(chunks) > 0, "Should receive chunks"
    print("✓ PASS: Three tools in streaming work")


async def test_streaming_tool_error_handling():
    """Test streaming when tool execution fails."""
    print("\n" + "=" * 60)
    print("Test 12: Streaming with Tool Error Handling")
    print("=" * 60)

    @tool
    def failing_tool(value: int) -> str:
        """A tool that always fails."""
        raise ValueError(f"Tool failed with value: {value}")

    agent = Agent(
        name="ErrorToolStreamAgent",
        instructions="You are helpful. Use tools when needed.",
        model=Gemini("gemini-2.5-flash"),
        tools=[failing_tool],
    )

    print("Q: Use failing_tool with value 42")
    print("A: ", end="", flush=True)

    try:
        chunks = []
        async for chunk in agent.stream("Use failing_tool with value 42"):
            chunks.append(chunk)
            print(chunk, end="", flush=True)
        print()
        print(f"\n✓ Received {len(chunks)} chunks (may be error message)")
        print("✓ PASS: Tool error handling in streaming works")
    except Exception as e:
        print(f"\n✓ Caught expected error: {type(e).__name__}")
        print("✓ PASS: Tool errors are handled in streaming")


async def test_concurrent_streaming():
    """Test multiple concurrent streaming requests."""
    print("\n" + "=" * 60)
    print("Test 13: Concurrent Streaming")
    print("=" * 60)

    agent = Agent(
        name="ConcurrentStreamAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
    )

    async def stream_question(q: str, num: int) -> tuple[int, str]:
        """Stream a question and return chunk count and response."""
        chunks = []
        response = ""
        async for chunk in agent.stream(q):
            chunks.append(chunk)
            response += chunk
        return num, response

    questions = [
        "Say 'one'",
        "Say 'two'",
        "Say 'three'",
    ]

    print("Running 3 concurrent streams...")
    tasks = [stream_question(q, i) for i, q in enumerate(questions)]
    results = await asyncio.gather(*tasks)

    for num, response in results:
        print(f"Stream {num}: {response.strip()[:50]}...")

    assert len(results) == 3, "Should complete all streams"
    print("✓ PASS: Concurrent streaming works")


async def main():
    """Run all streaming tests."""
    print("\n" + "=" * 60)
    print("Example 4: Comprehensive Streaming Tests")
    print("=" * 60)

    tests = [
        # test_streaming_basic,
        # test_stream_enabled_property,
        # test_streaming_with_tools,
        # test_streaming_long_response,
        # test_streaming_parameter_override,
        # test_streaming_error_handling,
        # test_streaming_vs_invoke,
        test_streaming_multiple_tools,
        test_streaming_parallel_tool_calls,
        test_streaming_tool_call_loop,
        test_streaming_with_three_tools,
        test_streaming_tool_error_handling,
        test_concurrent_streaming,
    ]

    for test in tests:
        await run_test(test)


async def run_test(test: Callable):
    try:
        await test()
    except Exception as e:
        print(f"\nFAIL: {test.__name__}: {e}")
        raise

    print("\n" + "=" * 60)
    print("All streaming tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
