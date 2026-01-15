"""
Example: Combined Input and Output Middleware

This example demonstrates using both input and output middlewares together
to create a complete processing pipeline.
"""

import asyncio
import os
from typing import Any

from framework.agents import Agent
from framework.middlewares import InputMiddleware, MiddlewareContext, OutputMiddleware
from framework.models import Gemini


class LoggingInputMiddleware(InputMiddleware):
    """Logs all input messages."""

    async def process(
        self, messages: list[dict[str, Any]], context: MiddlewareContext
    ) -> list[dict[str, Any]]:
        print(f"\n[Input Middleware] Thread: {context.thread_id}")
        print(f"[Input Middleware] Processing {len(messages)} messages")
        for i, msg in enumerate(messages):
            print(f"  Message {i}: {msg['role']} - {msg['content'][:50]}...")
        return messages


class ProfanityFilterMiddleware(OutputMiddleware):
    """Filters profanity from responses."""

    async def process(self, response: Any, context: MiddlewareContext) -> Any:
        print("\n[Output Middleware] Checking response for profanity")

        if hasattr(response, "content") and response.content:
            # Simple demo filter
            bad_words = ["bad", "terrible", "awful"]
            content = response.content
            for word in bad_words:
                if word in content.lower():
                    print(f"[Output Middleware] Filtered word: {word}")
                    content = content.replace(word, "***")
                    content = content.replace(word.capitalize(), "***")
            response.content = content

        return response


async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY environment variable.")
        return

    model = Gemini(model_id="gemini-1.5-flash", api_key=api_key)

    # Initialize agent with both middleware types
    agent = Agent(
        name="FilteredAgent",
        model=model,
        instructions="You are a helpful assistant.",
        input_middlewares=[LoggingInputMiddleware()],
        output_middlewares=[ProfanityFilterMiddleware()],
    )

    print("--- Starting Combined Middleware Test ---")

    response = await agent.invoke("Tell me about a bad day.", thread_id="test-thread-123")

    print(f"\n[Final Response]: {response}")


if __name__ == "__main__":
    asyncio.run(main())
