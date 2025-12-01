"""
Example: Output Middleware

This example demonstrates how to use OutputMiddleware to intercept and modify
the model's response before it is returned to the user.
"""

import asyncio
import os
from typing import Any

from framework.agents import Agent
from framework.middlewares import MiddlewareContext, OutputMiddleware
from framework.models import Gemini


class UppercaseMiddleware(OutputMiddleware):
    """Converts model responses to uppercase."""

    async def process(self, response: Any, context: MiddlewareContext) -> Any:
        print(f"\n[Middleware] Processing response for agent: {context.agent.name}")

        # Modify the response content
        if hasattr(response, "content") and response.content:
            original = response.content
            response.content = response.content.upper()
            print(f"[Middleware] Transformed: {original[:30]}... -> {response.content[:30]}...")

        return response


async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY environment variable.")
        return

    model = Gemini(model_id="gemini-1.5-flash", api_key=api_key)

    # Initialize agent with output middleware
    agent = Agent(
        name="LoudAgent",
        model=model,
        instructions="You are a helpful assistant.",
        output_middlewares=[UppercaseMiddleware()],
    )

    print("--- Starting Output Middleware Test ---")

    response = await agent.invoke("Tell me a short joke.")

    print(f"\n[Final Response]: {response}")


if __name__ == "__main__":
    asyncio.run(main())
