"""
Example 2: Agent with Tools
Tests tool execution, error handling, and retry logic.
"""

import asyncio

from framework.agents import Agent, tool
from framework.models import Gemini


# Define tools
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
    print(f"  [TOOL] calculator({operation}, {a}, {b}) = {result}")
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
    # Mock weather data
    weather_data = {
        "london": "Rainy, 15°C",
        "paris": "Sunny, 22°C",
        "new york": "Cloudy, 18°C",
        "tokyo": "Clear, 25°C",
    }

    city_lower = city.lower()
    weather = weather_data.get(city_lower, f"Weather data not available for {city}")
    print(f"  [TOOL] get_weather({city}) = {weather}")
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
    # Simulate async operation
    await asyncio.sleep(0.5)
    result = f"Search results for '{query}': [Mock result 1, Mock result 2, Mock result 3]"
    print(f"  [TOOL] search_web({query}) = {result}")
    return result


async def main():
    """Agent with tools example."""

    print("Agent with Tools")

    # Create agent with tools
    agent = Agent(
        name="ToolAgent",
        instructions="""You are a helpful assistant with access to tools.
        When asked to perform calculations, use the calculator tool.
        When asked about weather, use the get_weather tool.
        When asked to search, use the search_web tool.
        Always use tools when appropriate.""",
        model=Gemini("gemini-2.5-flash"),
        tools=[calculator, get_weather, search_web],
        temperature=0.3,
        max_retries=3,
    )

    tools_count = len(agent.tools) if agent.tools else 0
    tools_names = [t.name for t in agent.tools] if agent.tools else []
    print(f"Created agent with {tools_count} tools")
    print(f"  Tools: {tools_names}")

    # # Test 1: Calculator tool
    # print("\nTest 1: Calculator Tool")
    # response = await agent.invoke("What is 25 multiplied by 4?")
    # print("Q: What is 25 multiplied by 4?")
    # print(f"A: {response}")

    # # Test 2: Weather tool
    # print("\nTest 2: Weather Tool")
    # response = await agent.invoke("What's the weather like in Paris?")
    # print("Q: What's the weather like in Paris?")
    # print(f"A: {response}")

    # Test 3: Async tool (web search)
    # print("\nTest 3: Async Web Search Tool")
    # response = await agent.invoke("Search for 'Python programming tutorials'")
    # print("Q: Search for 'Python programming tutorials'")
    # print(f"A: {response}")

    # Test 4: Multiple operations
    # print("\nTest 4: Multiple Tool Calls")
    # response = await agent.invoke("Calculate 100 divided by 5, then add 10 to the result")
    # print("Q: Calculate 100 divided by 5, then add 10 to the result")
    # print(f"A: {response}")

    # Test 5: Error handling (invalid city)
    print("\nTest 5: Tool with Missing Data")
    response = await agent.invoke("What's the weather in Mumbai?")
    print("Q: What's the weather in Mumbai?")
    print(f"A: {response}")

    print("\nAll tool tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
