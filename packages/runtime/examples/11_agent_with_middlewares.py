"""Agent with middlewares example - CONCEPT DEMONSTRATION

NOTE: This is a concept demonstration showing middleware APIs.

Shows:
- Input middleware concept
- Output middleware concept
- Middleware chaining
"""

import asyncio

from astra import Agent
from astra import HuggingFaceLocal


async def main():
    """
    Concept demonstration of middlewares for request/response processing.
    """
    
    print("=== Astra Agent Middlewares (Concept Demo) ===\n")
    
    # Create basic agent
    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a helpful assistant that provides concise answers.",
        name="middleware-demo",
    )
    
    # Test basic interaction
    print("Example Query\n")
    response = await agent.invoke("What is Python?")
    print(f"Response: {response}\n")
    
    print("=" * 60)
    print("Middlewares Concept Overview")
    print("=" * 60)
    
    print("\n📥 **Input Middlewares**:")
    print("  Process incoming requests before they reach the agent")
    print("  - Logging: Track all requests")
    print("  - Validation: Ensure input meets requirements")
    print("  - Transformation: Preprocess input data")
    print("  - Authentication: Verify user identity")
    
    print("\n📤 **Output Middlewares**:")
    print("  Process agent responses before returning to user")
    print("  - Formatting: Apply consistent styling")
    print("  - Metrics: Collect response statistics")
    print("  - Caching: Store responses for reuse")
    print("  - Translation: Convert to different languages")
    
    print("\n📋 **How to create custom middleware**:")
    print("""
    from astra import InputMiddleware, OutputMiddleware, MiddlewareContext
    
    class LoggingMiddleware(InputMiddleware):
        async def process_input(self, input_data: str, context: MiddlewareContext) -> str:
            print(f"Input: {input_data}")
            # Store data in context.extra for access by other middlewares
            context.extra["input_logged"] = True
            return input_data
    
    class FormattingMiddleware(OutputMiddleware):
        async def process_output(self, output_data: str, context: MiddlewareContext) -> str:
            # Access data from context  
            input_logged = context.extra.get("input_logged", False)
            return f"✨ {output_data} ✨"
    
    # Use with agent
    agent = Agent(
        model=model,
        input_middlewares=[LoggingMiddleware()],
        output_middlewares=[FormattingMiddleware()],
    )
    """)
    
    print("\n✨ **Benefits**:")
    print("  ✓ Separation of concerns")
    print("  ✓ Reusable components")
    print("  ✓ Easy logging and monitoring")
    print("  ✓ Flexible request/response pipeline")


if __name__ == "__main__":
    asyncio.run(main())
