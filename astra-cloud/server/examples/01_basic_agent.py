"""Basic embedded mode example - demonstrates direct agent usage."""

import asyncio

from astra import Agent
from astra import HuggingFaceLocal


async def main():
    """
    Simple example of using an agent in embedded mode.

    No server, no HTTP - just direct Python execution.
    Perfect for scripts, background jobs, notebooks.
    """

    # Create an agent with Model instance
    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a helpful assistant that responds concisely",
        name="assistant",
    )

    # Use the agent
    print("Asking agent: 'What is 2+2?'")
    response = await agent.invoke("What is 2+2?")
    print(f"Agent response: {response}\n")

    # Another question
    print("Asking agent: 'Explain Python in one sentence'")
    response = await agent.invoke("Explain Python in one sentence")
    print(f"Agent response: {response}")


if __name__ == "__main__":
    print("=== Astra Embedded Mode Example ===\n")
    asyncio.run(main())
