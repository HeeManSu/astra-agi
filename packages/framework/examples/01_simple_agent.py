"""
Example 1: Simple Agent Invocation
Tests basic invoke functionality with no tools.
"""

import asyncio

from framework.agents import Agent
from framework.models import Gemini


async def main():
    """Simple agent invocation example."""

    # Create agent
    agent = Agent(
        name="SimpleAssistant",
        instructions="You are a helpful assistant. Be concise and clear.",
        model=Gemini("gemini-2.5-flash"),
        temperature=0.7,
        max_tokens=500,
        max_retries=1,
    )

    print(f"Created agent: {agent}")

    # Test 1: Basic question
    response = await agent.invoke("What is 2+2?")
    print("Q: What is 2+2?")
    print(f"A: {response}")

    # Test 2: Longer response
    response = await agent.invoke("Explain what Python is in 2 sentences.")
    print("Q: Explain what Python is in 2 sentences.")
    print(f"A: {response}")

    # Test 3: Parameter override
    response = await agent.invoke(
        "Say hello in a creative way",
        temperature=1.5,  # Higher temperature for more creativity
    )
    print("Q: Say hello in a creative way (temp=1.5)")
    print(f"A: {response}")

    # Test 4: Streaming
    print("Q: Tell me a very short joke")
    print("A: ", end="", flush=True)
    async for chunk in agent.stream("Tell me a very short joke"):
        print(chunk, end="", flush=True)
    print()  # New line

    print("All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
