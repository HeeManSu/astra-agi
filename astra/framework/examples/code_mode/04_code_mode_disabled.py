"""
Example 4: Code Mode Disabled

Demonstrates agent with code_mode=False (traditional tool calling).
"""

import asyncio
import os
import sys


# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from framework.agents import Agent
from framework.agents.tool import tool
from framework.models import Gemini


@tool
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    return {"city": city, "temperature": 72, "condition": "Sunny"}


async def main():
    # Create agent with code_mode disabled
    agent = Agent(
        name="WeatherAgent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="You are a weather assistant.",
        tools=[get_weather],
        code_mode=False,  # Disable code mode - use traditional tool calling
    )

    response = await agent.invoke("What's the weather in San Francisco?")
    print(f"Response: {response}")

    # Registry is still populated (for future use)
    print(f"\nTool registry populated: {len(agent.tool_registry)} tools")
    print(f"Code mode enabled: {agent.code_mode}")


if __name__ == "__main__":
    asyncio.run(main())
