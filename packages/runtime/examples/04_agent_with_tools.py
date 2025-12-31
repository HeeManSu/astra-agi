"""Agent with tools example - demonstrates tool usage."""

import asyncio

from astra import Agent
from astra import HuggingFaceLocal
from framework.agents import tool


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
    Get weather information for a city.

    Args:
        city: Name of the city

    Returns:
        Weather description
    """
    # Simulated weather data
    weather_data = {
        "paris": "Sunny, 22°C",
        "london": "Cloudy, 15°C",
        "tokyo": "Rainy, 18°C",
        "new york": "Clear, 20°C",
    }

    city_lower = city.lower()
    weather = weather_data.get(city_lower, "Weather data not available")
    print(f"  [TOOL] get_weather({city}) = {weather}")
    return weather


async def main():
    """Example of using an agent with tools."""

    print("=== Agent with Tools Example ===\n")

    # Create agent with tools
    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="""You are a helpful assistant with access to tools.
        When asked to perform calculations, use the calculator tool.
        When asked about weather, use the get_weather tool.
        Always use tools when appropriate.""",
        name="tool-agent",
        tools=[calculator, get_weather],
        temperature=0.3,
        max_retries=3,
    )

    print(f"Created agent: {agent.name}")
    print(f"Agent ID: {agent.id}\n")

    # Test 1: Calculator tool
    print("Test 1: Calculator Tool")
    print("Question: What is 25 multiplied by 4?")
    response = await agent.invoke("What is 25 multiplied by 4?")
    print(f"Response: {response}\n")

    # Test 2: Weather tool
    print("Test 2: Weather Tool")
    print("Question: What's the weather like in Paris?")
    response = await agent.invoke("What's the weather like in Paris?")
    print(f"Response: {response}\n")

    # Test 3: Multiple operations
    print("Test 3: Multiple Tool Calls")
    print("Question: Calculate 100 divided by 5, then add 10 to the result")
    response = await agent.invoke("Calculate 100 divided by 5, then add 10 to the result")
    print(f"Response: {response}\n")

    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
