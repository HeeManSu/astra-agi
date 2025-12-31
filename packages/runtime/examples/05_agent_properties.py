"""Agent properties example - demonstrates accessing agent properties."""

import asyncio

from astra import Agent
from astra import HuggingFaceLocal


async def main():
    """
    Example of accessing agent properties.

    Agent properties provide information about the agent configuration
    and can be useful for debugging, logging, or dynamic behavior.
    """

    print("=== Agent Properties Example ===\n")

    # Create an agent
    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a helpful coding assistant",
        name="coding-assistant",
        temperature=0.7,
        max_tokens=1000,
    )

    # Access agent properties
    print("Agent Information:")
    print(f"  ID: {agent.id}")
    print(f"  Name: {agent.name}")
    print(f"  Instructions: {agent.instructions}")
    print(f"  Model: {agent.model}")
    print(f"  Model ID: {agent.model.model_id}")
    print(f"  Model Provider: {agent.model.provider}")

    # Use the agent
    print("\nUsing the agent...")
    response = await agent.invoke("What is a decorator in Python?")
    print(f"\nResponse: {response[:100]}...")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
