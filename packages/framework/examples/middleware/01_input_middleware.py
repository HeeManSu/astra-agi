"""
Example: Input Middleware

This example demonstrates how to use InputMiddleware to intercept and modify messages
before they are sent to the model. We'll implement a simple PII redaction middleware.
"""

import asyncio
import os
from typing import Any

from framework.agents import Agent
from framework.middlewares import InputMiddleware, MiddlewareContext
from framework.models import Gemini


class PIIRedactionMiddleware(InputMiddleware):
    """Redacts phone numbers from user messages."""

    async def process(
        self, messages: list[dict[str, Any]], context: MiddlewareContext
    ) -> list[dict[str, Any]]:
        print(f"\n[Middleware] Processing {len(messages)} messages for agent: {context.agent.name}")

        for msg in messages:
            if msg["role"] == "user":
                content = msg["content"]
                # Simple fake redaction for demo
                if "555-0100" in content:
                    print(f"[Middleware] Redacting phone number in message: {content[:20]}...")
                    msg["content"] = content.replace("555-0100", "[REDACTED]")

        return messages


async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY environment variable.")
        return

    model = Gemini(model_id="gemini-1.5-flash", api_key=api_key)

    # Initialize agent with middleware
    agent = Agent(
        name="SecurityAgent",
        model=model,
        instructions="You are a helpful assistant. Always confirm what you received.",
        input_middlewares=[PIIRedactionMiddleware()],
    )

    print("--- Starting Middleware Test ---")

    # Send a message with sensitive data
    response = await agent.invoke("My phone number is 555-0100. Please call me.")

    print(f"\n[Agent Response]: {response}")


if __name__ == "__main__":
    asyncio.run(main())
