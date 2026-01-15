"""Advanced configuration example - demonstrates agent configuration options."""

import asyncio

from astra import Agent
from astra import HuggingFaceLocal


async def main():
    """
    Example of configuring an agent with advanced options.

    This demonstrates:
    - Temperature control
    - Max tokens limit
    - Max retries
    - Custom agent ID
    - Description
    """

    print("=== Advanced Configuration Example ===\n")

    # Create agent with advanced configuration
    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a creative writing assistant. Write engaging and imaginative stories.",
        name="creative-writer",
        id="writer-001",  # Custom ID
        description="A creative writing assistant specialized in storytelling",
        temperature=0.9,  # Higher temperature for more creativity
        max_tokens=500,  # Limit response length
        max_retries=5,  # More retries for reliability
    )

    print("Agent Configuration:")
    print(f"  ID: {agent.id}")
    print(f"  Name: {agent.name}")
    print(f"  Instructions: {agent.instructions[:50]}...")
    print(f"  Model: {agent.model.model_id}")
    print("  Temperature: 0.9 (high creativity)")
    print("  Max Tokens: 500")
    print("  Max Retries: 5\n")

    # Test with creative prompt
    print("Testing creative writing...")
    response = await agent.invoke(
        "Write a short story about a robot learning to paint, in 3 sentences."
    )
    print(f"Response: {response}\n")

    # Create another agent with different configuration
    print("Creating analytical agent with low temperature...")
    analytical_agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a precise analytical assistant. Provide accurate, factual answers.",
        name="analytical-assistant",
        temperature=0.1,  # Low temperature for precision
        max_tokens=200,  # Shorter responses
    )

    print("Testing analytical response...")
    response = await analytical_agent.invoke("What is 2+2? Explain briefly.")
    print(f"Response: {response}\n")

    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
