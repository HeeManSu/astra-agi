"""Streaming example - demonstrates streaming agent responses."""

import asyncio

from astra import Agent, HuggingFaceLocal


async def main():
    """
    Example of streaming agent responses.

    Streaming is useful for:
    - Real-time user feedback
    - Long responses that should appear incrementally
    - Better UX in interactive applications
    """

    # Create an agent
    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a helpful assistant that explains concepts clearly",
        name="streaming-assistant",
    )

    print("=== Streaming Example ===\n")
    print("Question: Explain how Python async/await works\n")
    print("Response (streaming):\n")

    # Stream the response
    async for chunk in agent.stream("Explain how Python async/await works in 3 sentences"):
        # Print each chunk as it arrives
        print(chunk, end="", flush=True)

    print("\n\n=== Streaming Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
