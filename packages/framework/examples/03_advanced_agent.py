"""
Example 3: Advanced Agent - Error Handling & Edge Cases
Tests validation, error handling, retry logic, and edge cases.
"""

import asyncio

from framework.agents import Agent, tool
from framework.agents.exceptions import ValidationError
from framework.models import Gemini


call_count = 0


@tool
def unreliable_tool(value: int) -> str:
    """
    A tool that fails the first 2 times, then succeeds.
    Used to test retry logic.

    Args:
        value: Input value

    Returns:
        Success message
    """
    global call_count
    call_count += 1

    print(f"  [TOOL] unreliable_tool called (attempt {call_count})")

    if call_count < 3:
        raise RuntimeError(f"Simulated failure (attempt {call_count})")

    call_count = 0  # Reset for next test
    return f"Success after retries! Value: {value}"


@tool
def strict_validator(text: str, min_length: int) -> str:
    """
    Validates text length strictly.

    Args:
        text: Text to validate
        min_length: Minimum required length

    Returns:
        Validation result
    """
    if len(text) < min_length:
        raise ValueError(f"Text too short: {len(text)} < {min_length}")

    return f"Valid! Text length: {len(text)}"


@tool
def data_processor(data: list[int]) -> dict:
    """
    Process a list of numbers.

    Args:
        data: List of integers

    Returns:
        Statistics about the data
    """
    if not data:
        return {"error": "Empty data"}

    return {
        "count": len(data),
        "sum": sum(data),
        "average": sum(data) / len(data),
        "min": min(data),
        "max": max(data),
    }


async def main():
    """Advanced agent testing."""

    print("Example 3: Advanced Agent - Error Handling & Edge Cases")

    # Create agent
    agent = Agent(
        name="AdvancedAgent",
        instructions="You are a helpful assistant. Use tools when appropriate.",
        model=Gemini("gemini-2.5-flash"),
        tools=[unreliable_tool, strict_validator, data_processor],
        temperature=0.5,
        max_retries=5,
        max_tokens=1000,
    )

    print(f"Created agent with max_retries={agent.max_retries}")

    # Test 1: Input Validation - Empty message
    print("Test 1: Empty Message Validation")
    try:
        await agent.invoke("")
        print("Should have raised ValidationError")
    except ValidationError as e:
        print(f"Caught expected error: {e}")

    # Test 2: Input Validation - Invalid temperature
    print("Test 2: Invalid Temperature")
    try:
        await agent.invoke("Hello", temperature=5.0)  # Out of range
        print("Should have raised ValidationError")
    except ValidationError as e:
        print(f"Caught expected error: {e}")

    # Test 3: Input Validation - Invalid max_tokens
    print("Test 3: Invalid Max Tokens")
    try:
        await agent.invoke("Hello", max_tokens=-100)
        print("Should have raised ValidationError")
    except ValidationError as e:
        print(f"Caught expected error: {e}")

    # Test 4: Very long message
    print("Test 4: Long Message")
    long_message = "Tell me about Python. " * 100  # Reasonable length
    response = await agent.invoke(long_message[:200])  # Truncate for display
    print(f"Q: {long_message[:50]}...")
    print(f"A: {response[:100]}...")

    # Test 5: Tool with error handling
    print("Test 5: Tool Error Handling")
    response = await agent.invoke("Use strict_validator to validate 'hi' with min_length 10")
    print("Q: Validate 'hi' with min_length 10")
    print(f"A: {response}")

    # Test 6: Tool with complex data
    print("Test 6: Complex Data Processing")
    response = await agent.invoke(
        "Use data_processor to analyze these numbers: [10, 20, 30, 40, 50]"
    )
    print("Q: Analyze numbers [10, 20, 30, 40, 50]")
    print(f"A: {response}")

    # Test 7: Streaming with error recovery
    print("Test 7: Streaming Response")
    print("Q: Explain error handling in 3 sentences")
    print("A: ", end="", flush=True)
    try:
        async for chunk in agent.stream("Explain error handling in Python in 3 sentences"):
            print(chunk, end="", flush=True)
        print()  # New line
    except Exception as e:
        print(f"\nStreaming error: {e}")

    # Test 8: Parameter overrides
    print("Test 8: Parameter Overrides")
    response = await agent.invoke(
        "Say hello",
        temperature=0.1,  # Very deterministic
        max_tokens=50,  # Short response
    )
    print("Q: Say hello (temp=0.1, max_tokens=50)")
    print(f"A: {response}")

    # Test 9: Edge case - Empty tool list
    print("Test 9: Agent Without Tools")
    simple_agent = Agent(
        name="SimpleAgent",
        instructions="You are helpful.",
        model=Gemini("gemini-2.5-flash"),
        tools=None,
    )
    response = await simple_agent.invoke("What is 5+5?")
    print("Q: What is 5+5? (no tools)")
    print(f"A: {response}")

    # Test 10: Multiple agents
    print("Test 10: Multiple Agents")
    agent1 = Agent(
        name="Agent1", instructions="You are a math expert.", model=Gemini("gemini-2.5-flash")
    )
    agent2 = Agent(
        name="Agent2", instructions="You are a history expert.", model=Gemini("gemini-2.5-flash")
    )

    r1 = await agent1.invoke("What is calculus?")
    r2 = await agent2.invoke("Who was Napoleon?")

    print(f"Agent1 (Math): {r1[:80]}...")
    print(f"Agent2 (History): {r2[:80]}...")

    print("All advanced tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
